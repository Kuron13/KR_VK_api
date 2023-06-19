from pprint import pprint
import json
import requests

class YaUploader:
    def __init__(self, token_yd: str):
        self.token = token_yd

    # def upload(self, list_photos):
    def upload(self, data):
        """Загрузка файлов на яндекс диск"""
        print(self.token)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'OAuth {self.token}'
        }
        upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'

        # Создание общей папки на Яндекс-диск
        folder_url = 'https://cloud-api.yandex.net/v1/disk/resources/'
        params = {'path': 'VK_photos'}
        response = requests.put(folder_url, headers=headers, params=params)
        if response.status_code == 201:
            print('Папка ВК успешно создана')
        elif response.status_code == 409:
            print('Такая папка ВК уже создана')
        else:
            print(f'При создании папки ВК произошла ошибка: {response.status_code}')

        # Создание папок альбомов на Яндекс-диск
        for album in data:
            folder_name = album['album_name']
            params = {'path': f'VK_photos/{folder_name}'}
            response = requests.put(folder_url, headers=headers, params=params)
            if response.status_code == 201:
                print(f'Папка альбома {folder_name} успешно создана')
            elif response.status_code == 409:
                print(f'Папка альбома {folder_name} уже создана')
            else:
                print(f'При создании папки альбома {folder_name} произошла ошибка: {response.status_code}')

        #Загрузка файлов на Яндекс-диск
            print(f"Загружено альбомов: {data.index(album)} из {len(data)}")
            for photo in album['photo_info']:
                params = {'path': f"VK_photos/{folder_name}/{photo['name']}",
                          'url': photo['url']}
                response = requests.post(upload_url, headers=headers, params=params)
                if response.status_code == 201 or response.status_code == 202:
                    print(f'Файл {photo["photo_id"]} успешно загружен')
                else:
                    print(f'При загрузке файла {photo["photo_id"]} произошла ошибка: {response.status_code}')
                print(f"Загружено фотографий: {album['photo_info'].index(photo)+1} из {album['count']} (Альбом: {album['album_name']})")
        print('Все фотографии загружены')

class VkApiHandler:
    base_url = 'https://api.vk.com/method/'
    def __init__(self, access_token, version='5.131'):
        self.params = {
            'access_token': access_token,
            'v': version}

    def get_user_photos(self, user_id):
        """Получение изображений из профиля ВК"""
        #Получение списка альбомов
        url_album = f'{self.base_url}photos.getAlbums'
        params_album = {'owner_id': user_id, 'photo_sizes': 1, 'need_system': 1, **self.params}
        response_album = requests.get(url_album, params=params_album)
        data_album = response_album.json()

        #Выбор альбомов для скачивания
        album_list = []
        print(f'У этого пользователя есть следующие альбомы:')
        for album in data_album['response']['items']:
            print(f"{data_album['response']['items'].index(album)+1}. {album['title']} ({album['size']} фото)")
        ids = input('Введите номера альбомов, которые хотите скачать, разделя их запятой (прим.: 1,2,7), или скачайте все альбомы сразу (all)')
        if ids == 'all':
            for album in data_album["response"]["items"]:
                album_list.append({'id': album['id'], 'name': album['title'], 'photos': [], 'count': 0})
        else:
            ids = ids.split(',')
            for id in ids:
                album_list.append({'id': data_album["response"]["items"][int(id)]['id'], 'name': data_album["response"]["items"][int(id)]['title'], 'photos': [], 'count': 0})

        #Получение фотографий из фльбомов
        if album_list:
            print(album_list)
            url = f'{self.base_url}photos.get'
            #подготовка id системных альбомов
            for album in album_list:
                album_id = album['id']
                if album['id'] < 0:
                    if album['id'] == -7:
                        album_id = 'profile'
                    elif album['id'] == -15:
                        album_id = 'wall'
                    elif album['id'] == -9000:
                        album_id = 'saved'
                #Получение фотографий
                params = {'owner_id': user_id, 'album_id': album_id, 'extended': 1, 'photo_sizes': 1, **self.params}
                response = requests.get(url, params=params)
                data = response.json()
                album['photos'].append(data)

                #Выбор количества фотографий, загружаемых на Яндекс-диск
                count_down = 5
                count_photos = len(data['response']['items'])
                if count_photos > 5:
                    all_photo = input(f"В альбоме \"{album['name']}\" {count_photos} фотографий. Скачать их все? (y/n)")
                    if all_photo == 'y':
                        count_down = count_photos
                    elif all_photo == 'n':
                        count_down = int(input(f'Сколько фотографий вы хотите скачать?'))
                    else:
                        print('Некорректный ввод. Будут скачаны первые 5 фотографий')
                if count_down > count_photos:
                    count_down = count_photos
                album['count'] = count_down

        #Сбор итогового списка всех альбомов со всеми фотографиями
        list_up = []
        for album in album_list:
            list_up.append({'album_name': album['name'], 'photo_info': self.find_info(album['count'], album), 'count': album['count']})

        return list_up

    def find_info(self, count_down, album):
        """Сбор информации о фотографиях"""
        data = album['photos']

        #Поск наибольшего размера изображений (профиль)
        sizes_photos = ['w', 'z', 'y', 'x', 'r', 'q', 'p', 'm', 'o', 's']
        list_photos = []
        #while count_down > 0:
        for photo in data[0]['response']['items']:
            max_size = '0'
            if count_down > 0:
                for type_size in sizes_photos:
                    if max_size != '0':
                        break
                    for size in photo['sizes']:
                        if size['type'] == type_size:
                            max_size = type_size
                            list_photos.append(
                                {'photo_id': photo['id'], 'album_id': photo['album_id'], 'max_size': type_size,
                                'url': size['url'], 'name': photo['likes']['count'],
                                'likes': photo['likes']['count'], 'date': photo['date']})
                            count_down -= 1
                            break

        #Переименование изображений
        for photo1 in list_photos:
            for photo2 in list_photos:
                if photo1['photo_id'] != photo2['photo_id']:
                    if photo1['likes'] == photo2['likes']:
                        photo1['name'] = f"{photo1['likes']}_{photo1['date']}"
                        photo2['name'] = f"{photo2['likes']}_{photo1['date']}"
                    else:
                        photo1['name'] = f"{photo1['likes']}"
                else:
                    photo1['name'] = f"{photo1['likes']}"

        #Запись информации об изображениях в json-файл
        with open('photo_data.json', 'a', encoding='utf-8', newline='') as f:
            data_json = []
            data_json.append({album['name']: []})
            for photo in list_photos:
                data_json[0][f"{album['name']}"].append({'file_name': photo['name'], 'size': photo['max_size']})
            json.dump(data_json, f, ensure_ascii=False, indent=2)

        return list_photos

if __name__ == '__main__':
    #Токен ВК
    with open('token.txt', 'r') as token_file:
        token = token_file.readline()
    #Инициализация класса ВК
    vk = VkApiHandler(token, '5.131')

    #Ввод ВК id пользователем
    user_id = input('Ведите id пользователя ВК, чьи альбомы вы хотите просмотреть: ')

    ### Получить токен Яндекс-диска от пользователя и инициализация класса ЯД
    token_yd = input('Введите token Яндекс-диска, в который будут загружаться фотографии: ')
    uploader = YaUploader(token_yd)

    #Работа с json и загрузка на ЯД
    data = vk.get_user_photos(user_id)
    uploader.upload(data)