from collections import OrderedDict
import requests
import urllib

from requests_toolbelt import MultipartEncoder
from bs4 import BeautifulSoup



class Icinga2BPUpload(object):

    ICINGA2_UPLOAD_ENDPOINT='/icingaweb2/businessprocess/process/upload'
    ICINGA2_CONFIG_ENDPOINT='/icingaweb2/businessprocess/process/config?config={}'
    ICINGA2_LOGIN_ENDPOINT='/icingaweb2/authentication/login'
    ICINGA2_ENDPOINT='/icingaweb2'

    predefined_auth_form_data = {
        'btn_submit': 'Login',
        'formUID': 'form_login',
    }

    def __init__(self, url, username, password):
        self.url =  url
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        self.auth_form_data = {
            'username': self.username,
            'password': self.password,
            'CSRFToken': None,
        }
        self.auth_form_data.update(
            self.predefined_auth_form_data)

        self.headers={
            'X-Icinga-Accept': 'text/html',
        }

    def do_post(self, endpoint, form_data):
        return self.session.post(
            urllib.parse.urljoin(self.url, endpoint),
            headers=self.headers,
            data=form_data
        )

    def do_get(self, endpoint):
        return self.session.get(
            urllib.parse.urljoin(self.url, endpoint)
        )

    def get_csrf_token(self, endpoint=None, name='CSRFToken'):
        response = self.do_get(endpoint or self.ICINGA2_ENDPOINT)
        if response.ok:
            handler = BeautifulSoup(response.text, "html.parser")
            return handler.find('input',
                {'name': name}).get('value')
        else:
            raise CSTFTokenNotFound(
                'Unable to find CSRFToken: {}:{} @ {}'.format(
                    response.status_code,
                    response.reason,
                    response.url
                )
            )

    def set_csrf_token(self, token):
        self.auth_form_data.update({
            'CSRFToken': token
        })
    
    def set_x_requested_by(self):
        self.headers.update({
            'X-Requested-With': 'XMLHttpRequest'
        })

    def set_content_type(self, form_data):
        multipart_form_data = MultipartEncoder(form_data,
            boundary='WebKitFormBoundary')
        self.headers.update({
            'Content-Type': multipart_form_data.content_type
        })
        return multipart_form_data

    def login(self):
        self.set_csrf_token(self.get_csrf_token())
        self.set_x_requested_by()
        return self.do_post(
            self.ICINGA2_LOGIN_ENDPOINT,
            self.auth_form_data    
        )

    def get_upload_status(self, headers):
        icinga_notification = headers.get('X-Icinga-Notification')
        if icinga_notification:
            return (True, urllib.parse.unquote(icinga_notification))
        return (False, str())

    def get_delete_status(self, headers):
        icinga_redirect = headers.get('X-Icinga-Redirect')
        if icinga_redirect:
            return (True, urllib.parse.unquote(icinga_redirect))
        return (False, str())     

    def delete(self, name):
        delete_csrf_token = self.get_csrf_token(
            self.ICINGA2_CONFIG_ENDPOINT.format(name),
            name='__FORM_CSRF'
        )
        form_data = OrderedDict([
            ('__FORM_NAME', 'IcingaModuleBusinessprocessFormsBpConfigForm'),
            ('__FORM_CSRF', delete_csrf_token),
            ('name', name),
            ('Delete', 'Delete'),
        ])
        response = self.do_post(
            self.ICINGA2_CONFIG_ENDPOINT.format(name),
            form_data
        )
        return self.get_delete_status(response.headers)

    def upload(self, name, source):
        upload_csrf_token = self.get_csrf_token(
            self.ICINGA2_UPLOAD_ENDPOINT,
            name='__FORM_CSRF'
        )
        form_data = OrderedDict([
            ('__FORM_NAME', 'IcingaModuleBusinessprocessFormsBpUploadForm'),
            ('__FORM_CSRF', upload_csrf_token),
            ('name', name),
            ('source', source),
            ('Store', 'Store'),
        ])

        form_data = self.set_content_type(form_data)
        response = self.do_post(
            self.ICINGA2_UPLOAD_ENDPOINT,
            form_data.to_string()
        )
        return self.get_upload_status(response.headers)

    def update(self, name, source):
        try:
            ok, result = self.delete(name)
            if ok:
                print('Conf deleted: {}'.format(result))
        except Exception as exc:
            print('Unable to delete: {}'.format(exc))

        try:
            ok, result = self.upload(name, source)
            if ok:
                print('Conf uploaded: {}'.format(result))
        except Exception as exc:
            print('Unable to upload: {}'.format(exc))


class CSTFTokenNotFound(Exception):
    pass


if __name__ == '__main__':
    handler = Icinga2BPUpload('http://some.icinga.url', 'username', 'password')
    handler.login()
    handler.update(config_name, open('some.conf','rb'))

