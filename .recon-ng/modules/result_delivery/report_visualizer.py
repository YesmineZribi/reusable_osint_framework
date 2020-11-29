# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality

# module specific imports


class Module(BaseModule):

    meta = {
        'name': 'Report_Visualizer',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': 'Resolves IP addresses to hosts and updates the database with the results.',
        'dependencies': ['Flask'],
        'files': [],
        'required_keys': [],
        'comments': (

        ),
        'options': (
            ('nameserver', '8.8.8.8', 'yes', 'ip address of a valid nameserver'),
        ),
    }


    def module_pre(self):
        pass

    def module_run(self):
        pass
