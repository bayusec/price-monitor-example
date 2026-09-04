import sys
import time

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.app_config import FirefoxConfig
import gzip
import brotli
from io import BytesIO


class SeleniumSession:
    def __init__(self):
        """
        Inicializa una sesión de Selenium con evasión básica para evitar detección.
        """

        profile = webdriver.FirefoxProfile()
        profile.set_preference("*******", False)
        profile.set_preference("*******", False)
        profile.set_preference("*******", False)
        profile.set_preference("*******", False)


        # Configuración del servicio y opciones
        self.service = Service(FirefoxConfig.gecko_path)
        self.options = Options()
        self.options.add_argument("--headless")  # Opcional: headless más detectable
        self.options.binary_location = FirefoxConfig.firefox_binary_path
        self.options.profile = profile

        # Inicialización del WebDriver
        self.driver = webdriver.Firefox(service=self.service, options=self.options)

        # Ejecutar evasión con JavaScript después de cargar el navegador
        self._evade_detection()

    def _evade_detection(self):
        """Ejecuta JavaScript para sobrescribir propiedades del navegador detectables."""
        script = """
            ****
        """
        try:
            self.driver.execute_script(script)
        except Exception as e:
            print("Error modificando propiedades del navegador via JS:", e)

    def _parse_netscape_cookies(self, cookies):
        """Convierte cookies en formato Netscape a cookies compatibles con Selenium."""
        parsed_cookies = []

        for line in cookies.splitlines():
            line = line.strip()
            # Ignorar líneas de encabezado o vacías
            if line.startswith("#") or not line:
                continue

            # Parsear la linea en formato Netscape
            parts = line.split("\t")
            if len(parts) != 7:
                print(f"Linea inválida: {line}")
                continue

            domain, flag, path, secure, expiration, name, value = parts

            # Convertir los valores al formato esperado por Selenium
            parsed_cookies.append({
                "domain": domain.strip(),
                "path": path.strip(),
                "secure": secure.strip().upper() == "TRUE",
                "expiry": int(expiration) if expiration.isdigit() else None,
                "name": name.strip(),
                "value": value.strip(),
            })

        return parsed_cookies

    def _set_cookies(self, cookies, wait_before_cookies=None, domain=None):
        """Establece las cookies en el navegador.
        :param cookies: Lista de diccionarios con cookies.
        """
        if not cookies:
            raise ValueError("Not cookies?")


        # Cargar el dominio para establecer las cookies
        if domain:
            self.driver.get(domain)

        # Espera hasta que el título contenga el texto especificado (si aplica)
        if wait_before_cookies:
            WebDriverWait(self.driver, 10).until(
                EC.title_contains(wait_before_cookies)
            )

        # Añadir cada cookie
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                print(f"Error añadiendo cookie {cookie}: {e}")

    def load_cookies_from_file(self, file_path):
        """Carga las cookies desde un archivo en formato Netscape HTTP Cookie."""
        with open(file_path, 'r') as file:
            cookies = file.read()
        parsed_cookies = self._parse_netscape_cookies(cookies)
        self._set_cookies(parsed_cookies, wait_before_cookies=None)

    def load_cookies_from_string(self, cookie_string, domain=None):
        cookie_list = []
        for c in cookie_string.split('; '):
            name, value = c.split('=')
            cookie_list.append({"name": name, "value": value})
        self._set_cookies(cookie_list, domain=domain)

    def get_page(self, url, wait_for=None, by=By.CLASS_NAME, timeout=15):
        """
        Carga la página y espera opcionalmente por un elemento.

        :param url: URL a cargar.
        :param wait_for: Selector del elemento a esperar.
        :param by: Tipo de selector (por defecto: By.CLASS_NAME).
        :param timeout: Tiempo máximo a esperar.
        :return: HTML de la página.
        """
        self.driver.get(url)

        if wait_for:
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, wait_for))
                )
            except Exception as e:
                print(f"[!] Timeout esperando '{wait_for}' en {url}: {e}")

        return self.driver.page_source

    def click_element(self, selector, type_selector=By.XPATH):
        element = self.driver.find_element(type_selector, selector)
        element.click()
        return element

    def find_element(self, type_selector=By.XPATH, selector=None, timeout=5):
        if selector is None:
            raise ValueError("Selector is required")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((type_selector, selector)))

    def wait_until(self, by, value, timeout=4, event='presence'):
        """
        Espera hasta que un elemento esté disponible.

        :param by: Tipo de localización (e.g., By.ID, By.CLASS_NAME, etc.).
        :param value: Valor del localizador.
        :param timeout: Tiempo máximo de espera en segundos (por defecto, 10).
        :return: El elemento localizado.
        """
        try:
            if event == 'presence':
                return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, value)))
            elif event == 'clickable':
                return WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, value)))

        except Exception as e:
            print(f"Error al esperar el elemento: {e}")
            return None

    def close(self):
        self.driver.quit()

    def get_driver(self):
        """Retorna el WebDriver de Selenium."""
        return self.driver

    def decode_response_body(self, response):
        """
        Decodifica automáticamente el body de una respuesta gzip/br/normal.
        :param response: request.response de selenium-wire
        :return: Texto decodificado (str)
        """
        body = response.body
        encoding = response.headers.get('Content-Encoding', '').lower()

        try:
            if 'gzip' in encoding:
                buf = BytesIO(body)
                return gzip.GzipFile(fileobj=buf).read().decode('utf-8')
            elif 'br' in encoding:
                return brotli.decompress(body).decode('utf-8')
            else:
                return body.decode('utf-8')
        except Exception as e:
            print(f"[!] Error decodificando body: {e}")
            return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("saliendo")
        self.close()
