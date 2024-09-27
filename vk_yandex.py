"""Модуль, обеспечивающий передачу фото из ВК на ЯндексДиск ."""
import json
import sys
import os
from time import sleep
from datetime import datetime
import requests
from tqdm import tqdm
import dotenv


def create_json_file(data, name_file):
    """Функция, обеспечивающая запись json файла с информ. о фотографиях
        data- json данные  name_file  - имя файла"""
    with open(name_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_idvk(string):
    """Функция, обеспечивающая ввод данных из консоли ."""
    while True:
        try:
            idf = int(input(string))
            return idf
        except ValueError:
            print("Вводите цифры. Повторите ввод")


def get_ext(string):  # забираем расширение у файла из урла
    """Функция, обеспечивающая получение маски расширения графич.файла из urlстроки."""
    if '?' in string:
        result = (string.split('?')[-2]).split('.')[-1]
    else:
        result = string.split('.')[-1]
    return result


def load_dotenv():
    """Функция, обеспечивающая получение данных из файла окружения."""
    dotenv.load_dotenv()
    dotenv.load_dotenv(dotenv.find_dotenv(filename='config.env', usecwd=True))


class YaApiClient:
    """Класс, обеспечивающий доступ к яндекс-клиенту"""

    def __init__(self, ya_tok):
        self.token = ya_tok

    def check_create_folder(self, name_folder):
        """метод проверяющий наличие запрашиваемой папки на ЯДиске,
        если ее нет, то создает новую"""

        url_api_ya = 'https://cloud-api.yandex.net/v1/disk/resources'
        # create_folder_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': name_folder}
        headers = {'Authorization': self.token}
        response = requests.put(url_api_ya,
                                headers=headers,
                                params=params,
                                timeout=10)
        result = ['', False]
        match response.status_code:
            case 409:
                result = ['Папка уже существует' + ' (ЯДиск)', True]
            case 507:
                result = ['Недостаточно свободного места' + ' (ЯДиск)', False]
            case 503:
                result = ['Сервис временно недоступен' + ' (ЯДиск)', False]
            case 429:
                result = ['Слишком много запросов.' + ' (ЯДиск)', False]
            case 423:
                result = [
                    'Технические работы. Сейчас можно только просматривать'
                    ' и скачивать файлы (ЯДиск)', False]
            case 406:
                result = [
                    'Ресурс не может быть представлен в запрошенном формате.'
                    + '(ЯДиск)', False]
            case 403:
                result = [
                    'API недоступно. Ваши файлы занимают больше места, чем у вас есть.'
                    ' Удалите лишнее или увеличьте объём Яндекс Диска.', False]
            case 401:
                result = ['Не авторизирован ' + ' ЯДиск', False]
            case 400:
                result = ['Некорректные данные.' + '( ЯДиск)', False]
            case 201:
                result = ['Ок.', True]

        return result

    def writing_data(self, data_writing, name_folder="images_from_VK"):
        """метод, обеспечивающий запись файлов из на ЯДиск  из списка урл """

        res = self.check_create_folder(name_folder)
        if not res[1]:
            print(res[0], '\n Прерываю работу.')
            sys.exit()

        for name_file, pic in tqdm(data_writing.items(),
                                   ncols=80,
                                   ascii=True,
                                   desc='Запись в облако'):
            url_link = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
            params = {'path': f'{name_folder}/{name_file}', 'overwrite': 1}
            headers = {'Authorization': self.token}
            response = requests.get(url_link,
                                    params=params,
                                    headers=headers,
                                    timeout=10)
            # print(response.status_code)
            # pprint(response.json())
            if response.status_code == 200:
                fil_temp = {'file': requests.get(pic, timeout=10).content}
                link_for_load = response.json()['href']
                resp = requests.put(link_for_load, files=fil_temp, timeout=10)

                if resp.status_code < 200 or resp.status_code > 299:
                    print('Ошибка при загрузке файла в облако', name_file)
            else:
                print('Ошибка при запросе ресурса для загрузки к ЯндексДиску')
                break


class VKApiClient:
    """Класс, обеспечивающий доступ к VK- возвращает словарь с двумя списками:
    список урл с фото и список для json-а"""

    URL_API = 'https://api.vk.com/method/photos.get'

    def __init__(self, access_token, us_id, yan, version='5.199'):
        self.token = access_token
        self.id = us_id
        self.version = version
        self.ya = yan
        self.params = {'access_token': self.token, 'v': self.version}

    def get_self_params(self):
        """ метод заполняет параметры в словарь для передачи в запрос  """
        return {
            'access_token': self.token,
            'v': self.version,
            #    'user_id':self.id
        }

    def get_profile_photos(self, cnt_pic=5):
        """" метод для выборки данных по фотографиям VK"""

        # url = 'https://api.vk.com/method/photos.get'
        params = self.get_self_params()
        params.update(
            {'owner_id': self.id, 'album_id': 'profile', 'extended': 1,
             'photo_sizes': 1, 'count': cnt_pic})
        response = requests.get(self.URL_API, params=params, timeout=10)
        try:
            resp_copy = response.json()['response']['items']
        except KeyError:  # Exception:
            print('Что-то пошло не так', '\nпохоже, что просрочен токен VK или'
                                         ' нет прав доступа к этому ресурсу')
            sys.exit()

        list_likes = []
        json_pack = []
        dict_urls = {}
        shema = '%d_%m_%Y__%H_%M_%S'
        for i_photo in tqdm(resp_copy,
                            ncols=80,
                            ascii=True,
                            desc='Поиск фотографий'):  # проходим по всему жисону
            sleep(0.1)
            max_letter = ''  # тут будем отбирать максимальную букву размера фото
            my_picture_is = ''
            for i_size in i_photo['sizes']:  # проходим по размерам
                if max_letter <= i_size[
                    'type']:  # ищем фотку по максимальному значению буковки
                    my_picture_is = i_size['url']
                    max_letter = i_size['type']
            likes = i_photo['likes']['count']
            if likes in list_likes:  # будем формировать имя файла фотографии согласно ТЗ
                name_file_pic = (f"pic_{str(likes)}"
                                 f"({datetime.fromtimestamp(int(i_photo['date'])).strftime(shema)})"
                                 f".{get_ext(my_picture_is)}")
            else:
                list_likes += [i_photo['likes']['count']]
                name_file_pic = f'pic_{str(likes)}.{get_ext(my_picture_is)}'

            json_pack.append({'file_name': name_file_pic,
                              'size': max_letter})  # добавляем в список словарей
            # (выходные данные см курсовой)
            dict_urls[name_file_pic] = my_picture_is
            # with open(f'img/{name_file_pic}', 'wb') as f:
            #     f.write(response.content)
        return [dict_urls, json_pack]  # на выходе словарь с урлами картинок,
        # и словарь с будущим жисоном-файлом


if __name__ == '__main__':
    load_dotenv()
    ya_token = os.getenv("YA_TOKEN")
    vk_token = os.getenv("VK_TOKEN")
    j_file = os.getenv("JSONFILE")
    user_id = get_idvk("Введите ID пользователя ВКонтакте:")
    COUNT_PIC = get_idvk("Количество запрашиваемых фото:")
    if COUNT_PIC == 0:
        COUNT_PIC = 5
    ya = YaApiClient(ya_token)
    vk = VKApiClient(vk_token, user_id, ya)
    data_pic = vk.get_profile_photos(COUNT_PIC)
    ya.writing_data(data_pic[0], 'Images_VK')
    create_json_file(data_pic[1], j_file)
