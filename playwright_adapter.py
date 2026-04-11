from playwright.sync_api import sync_playwright


class PlaywrightWebDriverAdapter:

    def __init__(self):
        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch()
        self.page = self.browser.new_page()

    def get(self, url):
        self.page.goto(url)

    def quit(self):
        self.browser.close()
        self.p.stop()