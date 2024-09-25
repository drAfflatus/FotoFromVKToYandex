import json
import sys
from time import sleep
from datetime import datetime
import requests
from tqdm import tqdm
import dotenv
import os




def create_json_file(data, name_file):
    with open(name_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_idvk(string):
    while True:
        try:
            idf = int(input(string))
            return idf
        except ValueError:
            print("Вводите цифры. Повторите ввод")




def get_ext(string):   # забираем расширение у файла из урла
   if '?' in string:
        result = (string.split('?')[-2]).split('.')[-1]
   else:
        result = (string.split('.')[-1])
   return result

def load_dotenv():
    dotenv.load_dotenv()
    dotenv.load_dotenv(dotenv.find_dotenv(filename='config.env',usecwd=True))

class YaApiClient:
    def __init__(self,ya_tok):
        self.token = ya_tok

    def check_create_folder(self,name_folder):
        url_api_ya = 'https://cloud-api.yandex.net/v1/disk/resources'
        # create_folder_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': name_folder}
        headers ={ 'Authorization' : self.token}
        response =requests.put(url_api_ya,headers=headers,params = params)
        result = ['',False]
        match response.status_code:
            case 409:
                result = ['Папка уже существует'+' (ЯДиск)',True]
            case 507:
                result = ['Недостаточно свободного места'+' (ЯДиск)',False]
            case 503:
                result = ['Сервис временно недоступен'+' (ЯДиск)',False]
            case 429:
                result = ['Слишком много запросов.'+' (ЯДиск)',False]
            case 423:
                result = ['Технические работы. Сейчас можно только просматривать и скачивать файлы.'+'(ЯДиск)',False]
            case 406:
                result = ['Ресурс не может быть представлен в запрошенном формате.'+'( ЯДиск)',False]
            case 403:
                result = ['API недоступно. Ваши файлы занимают больше места, чем у вас есть. Удалите лишнее или '
                          'увеличьте объём Яндекс Диска.',False]
            case 401:
                result = ['Не авторизирован '+' ЯДиск',False]
            case 400:
                result = ['Некорректные данные.'+'( ЯДиск)',False]
            case 201:
                result = ['Ок.',True]

        return result

    def writing_data(self,data_writing,name_folder="images_from_VK"):

        res = self.check_create_folder(name_folder)
        if not(res[1]):
            print(res[0], '\n Прерываю работу.')
            sys.exit()

        for name_file,pic in tqdm(data_writing.items(),ncols=80,ascii=True, desc='Запись в облако'):
            url_link =  'https://cloud-api.yandex.net/v1/disk/resources/upload'
            params = {'path': f'{name_folder}/{name_file}','overwrite':1}
            headers = {'Authorization': self.token}
            response = requests.get(url_link,params=params,headers=headers)
            #print(response.status_code)
            #pprint(response.json())
            if response.status_code == 200:
                link_for_load = response.json()['href']
                resp=requests.put(link_for_load,files ={'file' : requests.get(pic).content})

                if resp.status_code<200 or resp.status_code>299: print('Ошибка при загрузке файла в облако',name_file)
            else:
                print('Ошибка при запросе ресурса для загрузки к ЯндексДиску')
                break





class VKApiClient:

    #URL_API ='https://api.vk.com/method/status.get'

    def __init__(self, access_token, us_id, yan, version='5.199'):
        self.token = access_token
        self.id = us_id
        self.version = version
        self.ya = yan
        self.params = {'access_token': self.token, 'v': self.version}
    def get_self_params(self):
        return {
            'access_token':self.token,
            'v':self.version,
        #    'user_id':self.id
        }

    def get_profile_photos(self,cnt_pic=5):
        url = 'https://api.vk.com/method/photos.get'
        params = self.get_self_params()
        params.update({'owner_id':self.id, 'album_id':'profile', 'extended':1, 'photo_sizes':1, 'count': cnt_pic })
        response = requests.get(url,params=params)
        try:
            resp_copy = response.json()['response']['items']
        except KeyError: #Exception:
            print('Что-то пошло не так', '\nпохоже, что просрочен токен VK или нет прав доступа к этому ресурсу' )
            sys.exit()

        list_likes = []
        json_pack =[]
        dict_urls ={}
        for i_photo in tqdm(resp_copy,ncols=80,ascii=True, desc='Поиск фотографий'):  # проходим по всему жисону
            sleep(0.1)
            max_letter ='' # тут будем отбирать максимальную букву размера фото
            my_picture_is=''
            for i_size in i_photo['sizes']:  # проходим по размерам
                if max_letter <= i_size['type']: #  ищем фотку по максимальному значению буковки
                    my_picture_is = i_size['url']
                    max_letter = i_size['type']
            likes = i_photo['likes']['count']
            if likes in list_likes:    # будем формировать имя файла фотографии согласно ТЗ
                name_file_pic = f"pic_{str(likes)}({datetime.fromtimestamp(int(i_photo['date'])).strftime('%d_%m_%Y__%H_%M_%S')}).{get_ext(my_picture_is)}"
            else:
                list_likes += [i_photo['likes']['count']]
                name_file_pic = f'pic_{str(likes)}.{get_ext(my_picture_is)}'

            json_pack.append({'file_name':name_file_pic,'size':max_letter}) # добавляем в список словарей (выходные данные см задание курсовой)
            dict_urls[name_file_pic] = my_picture_is
            # with open(f'img/{name_file_pic}', 'wb') as f:
            #     f.write(response.content)
        return [dict_urls,json_pack] # на выходе словарь с урлами картинок, и словарь с будущим жисоном-файлом



if __name__ == '__main__':
    load_dotenv()
    ya_token = os.getenv("YA_TOKEN")
    vk_token = os.getenv("VK_TOKEN")
    j_file = os.getenv("JSONFILE")
    user_id = get_idvk("Введите ID пользователя ВКонтакте:")
    count_pic = get_idvk("Количество запрашиваемых фото:")
    if count_pic == 0: count_pic=5
    ya = YaApiClient(ya_token)
    vk = VKApiClient(vk_token, user_id,ya)
    data_pic=vk.get_profile_photos(count_pic)
    ya.writing_data(data_pic[0],'Images_VK')
    create_json_file(data_pic[1], j_file)
