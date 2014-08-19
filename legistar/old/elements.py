import io


class ElementAccessor:
    def get_text(self):
        ''' This is necessary to prevent idiocy of el.text_content()
        which sometimes doesn't add spaces.  '''
        buf = io.StringIO()
        first = True
        # TODO: this is useless, fix it
        for chunk in self.el.itertext():
            chunk = chunk.strip()
            if not chunk:
                continue
            if not first:
                buf.write(' ')
            buf.write(chunk)
            first = False
        text = buf.getvalue().strip()
        if not self._is_blank(text):
            return text

    def _is_blank(self, text):
        if not text:
            return True
        if text.strip().replace('\xa0', ' ') == 'Not available':
            return True

    def is_blank(self):
        return self._is_blank(self.text)

    def get_media_type(self):
        gif_url = None
        for xpath in ('string(.//img/@src)', 'string(..//img/@src)'):
            gif_url = self.el.xpath(xpath)
            if gif_url:
                break
        if gif_url:
            path = urlparse(gif_url).path
            key = path
        else:
            _, extension = self.get_url().rsplit('.', 1)
            key = extension
        return self.cfg.mediatypes.get(key.lower())

    def get_img_src(self):
        '''Returns the first string in the field data.
        '''
        return self.el.attrib.get('src')

    def get_media_url(self):
        '''Parse the url out of the onclick attr and make it
        absolute.
        '''
        onclick = self.el.xpath('string(.//a/@onclick)')
        if not onclick:
            return
        rel_url = re.findall(r"\('(.+?)'\,", onclick)
        url = urljoin(self.cfg.root_url, rel_url.pop())
        return url
