
from legistar.jxn_config import Config
from legistar.rootview import Root
from legistar.jurisdictions.nyc import Config as NycConfig

if __name__ == '__main__':
    import pprint
    jxn_config = type('Config', (NycConfig, Config,), {})
    site = Root(jxn_config)
    # print(site.get_active_tab())
    for obj in site.gen_events():
        pprint.pprint(obj.asdict())
        deets = obj.detail_page.asdict()
        import pdb; pdb.set_trace()
