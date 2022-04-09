from urllib import response
import requests
import datetime
import os
import json
from tqdm import tqdm


def get_token_id(file_name): # Функция для чтения токена и ID из файла
    with open(os.path.join(os.getcwd(), file_name), 'r') as token_file:
        token = token_file.readline().strip() # Строка с токеном
        id_one = token_file.readline().strip() # Строка с id 
    return [token, id_one]


def find_max_dpi(dict_in_search): # Функция возвращает ссылку на фото максимального размера и размер фото
    max_dpi = 0  # Задаем начальный размер фото для сравнения
    need_elem = 0 # Начальный индекс элемента 
    for j in range(len(dict_in_search)):
        file_dpi = dict_in_search[j].get('width') * dict_in_search[j].get('height') # Получение размера фото путем перемножения ширины и высоты в пикселях
        if file_dpi > max_dpi: # Сравнение текущего размера фото с максимальным 
            max_dpi = file_dpi # В случае верности равенства присваиваем новое значение для max_dpi
            need_elem = j
    return dict_in_search[need_elem].get('url'), dict_in_search[need_elem].get('type')  # Возвращаем URL и тип файла


def time_convert(time_unix): # Функция преобразования времени загрузки в параметрах фото
    time_bc = datetime.datetime.fromtimestamp(time_unix)
    str_time = time_bc.strftime('%Y-%m-%d time %H-%M-%S')
    return str_time


class Vk_photo:  # Создание класса для работы api vk
    def __init__(self, token_list, version='5.131'):
        self.token = token_list[0] # Начальное значение берется из функции чтения токена и id из файла которая возвращает список
        self.id = token_list[1] # с токеном и id
        self.version = version 
        self.start_params = {'access_token': self.token, 'v': self.version} # базовые параметры - токен доступа и версия api
        self.json, self.export_dict = self._photo_sorted()

    def _photo_info(self): #Получаем количество фото  и массив из параметров фотографий
        url = 'https://api.vk.com/method/photos.get' # Ссылка на метод 
        params = {'owner_id': self.id,
                  'album_id': 'profile',
                  'photo_sizes': 1,
                  'extended': 1,
                  'rev': 1
                  }
        photo_info = requests.get(url, params={**self.start_params, **params}).json()['response'] # Формирование запроса
        return photo_info['count'], photo_info['items'] # Возвращает информацию о количестве фото и параметры по ключу ['items']

    def _logs(self): # Помещаем параметы фотографий в словарь
        photo_count, photo_items = self._photo_info() # Берем результат из предыдущей функции
        result = {}
        for i in range(photo_count):
            likes_count = photo_items[i]['likes']['count']
            url_download, picture_size = find_max_dpi(photo_items[i]['sizes']) #Используем функцию для поиска макс dpi
            time_warp = time_convert(photo_items[i]['date']) # Конфертация времени из графы date
            new_value = result.get(likes_count, [])
            new_value.append({'likes_count': likes_count,
                              'add_name': time_warp,
                              'url_picture': url_download,
                              'size': picture_size})
            result[likes_count] = new_value
        return result

    def _photo_sorted(self): # Получаем словарь с параметрами фото и список для выгрузки
        json_list = []
        sorted_dict = {}
        picture_dict = self._logs() # Словарь берется из предыдущей функции
        counter = 0
        for elem in picture_dict.keys():
            for value in picture_dict[elem]:
                if len(picture_dict[elem]) == 1:
                    file_name = f'{value["likes_count"]}.jpeg'
                else:
                    file_name = f'{value["likes_count"]} {value["add_name"]}.jpeg' # При невыполнение условия к названию добавляем конвертированную дату
                json_list.append({'file name': file_name, 'size': value["size"]})
                if value["likes_count"] == 0:
                    sorted_dict[file_name] = picture_dict[elem][counter]['url_picture']
                    counter += 1
                else:
                    sorted_dict[file_name] = picture_dict[elem][0]['url_picture']
        return json_list, sorted_dict


class Yandex:
    def __init__(self, folder_name, token_list, num=5):    # Начальные параметры для загрузки на яндекс-диск
        self.token = token_list[0]
        self.added_files_num = num  # Кол-во загружаемых файлов 
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.headers = {'Authorization': self.token}
        self.folder = self._create_folder(folder_name) # Создание папки 

    def _create_folder(self, folder_name): # Функция создания папки 
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
               requests.put(url, headers=self.headers, params=params)
               print(f'\nПапка {folder_name} успешно создана n')
        else:
            print(f'\nПапка {folder_name} уже существует.\n')
        return folder_name

    def _in_folder(self, folder_name): # Получение ссылки для загрузки файлов на яндекс-диск
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        resource = requests.get(url, headers=self.headers, params=params).json()['_embedded']['items']
        in_folder_list = []
        for elem in resource:
            in_folder_list.append(elem['name'])
        return in_folder_list

    def create_copy(self, dict_files):
        """Метод загрузки фотографий на Я-диск"""
        files_in_folder = self._in_folder(self.folder)
        copy_counter = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.added_files_num))):
            if copy_counter < self.added_files_num:
                if key not in files_in_folder:
                    params = {'path': f'{self.folder}/{key}',
                              'url': dict_files[key],
                              'overwrite': 'false'}
                    requests.post(self.url, headers=self.headers, params=params)
                    copy_counter += 1
                else:
                    print(f'Внимание:Файл {key} уже существует')
            else:
                break

        print(f'\nЗапрос завершен, новых файлов скопировано (по умолчанию: 5): {copy_counter}'
              f'\nВсего файлов в исходном альбоме VK: {len(dict_files)}')


if __name__ == '__main__':

    tokenVK = 'token_id.txt'  # токен и id доступа хранятся в файле (построчно)
    tokenYandex = 'yandex_token.txt'  # хранится только токен яндекс диска

    photo_load_vk = Vk_photo(get_token_id(tokenVK))  # Получение JSON списка с информацией о фотографииях

    with open('photo.json', 'w') as outfile:  # Сохранение JSON списка ф файл my_VK_photo.json
        json.dump(photo_load_vk.json, outfile)


    my_yandex = Yandex('фото из вк', get_token_id(tokenYandex), 5)  # Создаем экземпляр класса Yandex с параметрами: "Имя папки", "Токен" и количество скачиваемых файлов
    my_yandex.create_copy(photo_load_vk.export_dict)  # Вызываем метод create_copy для копирования фотографий с VK на Я-диск