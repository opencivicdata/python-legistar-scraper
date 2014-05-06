import os
import datetime
import collections
import logging.config
from os.path import join, abspath, dirname

import banzai
from hercules import CachedAttr


class Settings:
    ROOT = dirname(dirname(abspath(__file__)))
    CACHE = join(ROOT, 'cache')
    DATA = join(ROOT, 'data')
    SCRAPELIB_TIMEOUT = 5
    SCRAPELIB_RPM = None
    SCRAPELIB_RETRY_ATTEMPTS = True
    SCRAPELIB_RETRY_WAIT_SECONDS = 0

settings = Settings()


class PipelineState:

    settings = settings

    def get_dir(self, root, *dirs):
        '''Get dir name based on command line args.
        '''
        path = [root]
        path.append(self.args.build_id)
        path.extend(list(dirs))
        path = os.path.join(*path)
        return path

    def configure_dir(self, root, *dirs):
        '''Given the jurisdiction indicated on the command line,
        calculate the path starting at root, and make sure it exists.
        '''
        path = self.get_dir(root, *dirs)
        try:
            os.makedirs(path)
            self.info('created dir %r' % path)
        except OSError:
            pass
        return path

    def get_data_dir(self, *dirs):
        return self.get_dir(settings.DATA, *dirs)

    def get_cache_dir(self, *dirs):
        return self.get_dir(settings.CACHE, *dirs)

    def configure_data_dir(self, *dirs):
        return self.configure_dir(settings.DATA, *dirs)

    def configure_cache_dir(self, *dirs):
        return self.configure_dir(settings.CACHE, *dirs)

    def configure_data_filename(self, *parts):
        parts = list(parts)
        filename = parts.pop()
        return os.path.join(self.configure_data_dir(*parts), filename)

    def configure_cache_filename(self, *parts):
        parts = list(parts)
        filename = parts.pop()
        return os.path.join(self.configure_cache_dir(*parts), filename)

    # -----------------------------------------------------------------------
    # Helpful stuff.
    # -----------------------------------------------------------------------
    @CachedAttr
    def client(self):
        return Client(self)

    @CachedAttr
    def urls(self):
        return Urls(self.client)



class Config:
    state_cls = PipelineState
    arguments = [
        (['prog'], dict(
            type=str,
            default='fail',
            help='Such failure.')),
        (['action'], dict(
            type=str,
            default='scrape',
            help='Scrape stuff.')),
        (['build_id'], dict(
            type=str,
            help='The build id to import.')),
        (['-f', '--fastmode'], dict(
            default=False,
            action='store_true',
            help='Deactivate scraper rate limit.')),]


class Delegator:

    scrape = dict(
        import_prefix='nyc_legistar.scrape.components',
        components=[
            'BillSpider',
            'ReportWriter',
            ])

    def __iter__(self):
        component_spec = getattr(self, self.args.action)
        yield from self.state.pipeline(**component_spec)


class Pipeline(banzai.Pipeline):
    config_obj = Config
    components = [Delegator]


def run():
    banzai.run(Pipeline)



if __name__ == '__main__':
    run()