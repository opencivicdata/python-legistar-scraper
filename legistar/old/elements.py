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
