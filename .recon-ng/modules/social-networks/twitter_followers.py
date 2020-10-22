# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.twitter import TwitterMixin
# module specific imports
import re

class Module(BaseModule, TwitterMixin):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'Twitter Recon',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': 'Leverage twitter API to get a user\'s followers',
        'required_keys': ['twitter_api', 'twitter_secret'],
        'comments': (
            '15 requests / 15 min window',
        ),
        'query': "SELECT DISTINCT username FROM profiles WHERE username IS NOT NULL AND resource LIKE 'Twitter' COLLATE NOCASE",
        'options': (
            ('limit', True, True, 'toggle rate limiting'),
            ('user_id', '', False, 'the ID of the user for whom to return results'),
            ('cursor', -1, True, 'causes results to be broken into pages. Default set to -1, which is the first \'page\''),
            ('count', 200, False, 'the number of users to return per page, up to a maximum of 200. Defaults to 20'),
            ('skip_status', 'false', False, 'when set to true, t, or 1, statuses will not be included in the returned objects. If set to any other value, statuses will be included'),
            ('include_user_entities', 'false', False, 'the user object entities node will not be included when set to false'),
        ),
    }

    # "name", "author", "version", and "description" are required entries
    # "dependencies" is required if the module requires the installation of a third party library (list of PyPI install names)
    # "files" is required if the module includes a reference to a data file in the "/data" folder of the marketplace repository
    # "required_keys" is required if the module leverages an API or builtin functionality that requires a key
    # "query" is optional and determines the "default" source of input
    # the "SOURCE" option is only available if "query" is defined
    # "options" expects a tuple of tuples containing 4 elements:
    # 1. the name of the option
    # 2. the default value of the option (strings, integers and boolean values are allowed)
    # 3. a boolean value (True or False) for whether or not the option is mandatory
    # 4. a description of the option
    # "comments" are completely optional

    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self, handles):
        for handle in handles:
            #Prepare the payload for each handle
            payload = {}
            for key,value in self.options.items():
                if 'source' not in key.lower() and 'limit' not in key.lower() and value != '':
                    payload[key.lower()] = str(value).lower() if type(value) is bool else value  #lower case the boolean values to put in the payload

            payload['screen_name'] = handle #source (ie username) is the screen_name
            self.heading(handle, level=0)
            results = self.followers_twitter_api(payload,self.options['limit'])
            
