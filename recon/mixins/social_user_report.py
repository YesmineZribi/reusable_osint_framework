from recon.core import framework
from recon.mixins.social_post import *
from recon.mixins.social_user import *
from recon.mixins.social_post import *
from enum import Enum
from collections import defaultdict

class UserReport(framework.Framework):

    def __init__(self,user,measures):
        framework.Framework.__init__(self, 'social_report')

        self.user = user
        self.measures = measures

    def graph_metric_format(self,graph_name,metrics):
        string_rep = f"Node metrics in {graph_name}\n"
        for metric,value in metrics.items():
            string_rep += f"\t{metric}: {value}\n"
        return string_rep


    def __repr__(self):
        string_rep = f"User screen name: {self.user.screen_name}\n"
        string_rep = f"User id: {self.user.id}\n"
        for graph_name,metric_dict in self.measures.items():
            string_rep += self.graph_metric_format(graph_name,metric_dict)
            string_rep += "\n\n"
        return string_rep

class RelationshipReport(framework.Framework):

    def __init__(self,user1,user2):
        framework.Framework.__init__(self, 'social_report')

        self.user1 = user1
        self.user2 = user2
        # Stores if the two users have common friends/followers
        self.common_connections = {}
        # Toggles for the different report sections
        self.connection_analysis = False
        self.reshare_analysis = False
        self.mention_analysis = False
        self.favortie_analysis = False
        self.comment_analysis = False

        # Flags for common functions
        self.common_reshare = False
        self.common_mention = False
        self.common_favorite = False
        self.common_comment = False
        # Stores reshares in which u1 reshared post by u2 or vice versa
        self.reshares = {}
        # Stores mentions in which u1 mentions u2 or vice versa
        self.mentions = {}
        # Stores posts from u1 and liked by u2 and vice versa
        self.favorites = {}
        # Stores comments from u1 of posts made by u2 and vice versa
        self.comments = {}
        # These will store all reshares by the target users from the same source
        # These include same posts reshared by u1 and u2 and different posts
        # but from the same source
        self.user1_reshares = {} #{src: CommonSrcReshares}
        self.user2_reshares = {} #{src: CommonSrcReshares}
        # These will store all mentions by the target users from the same source
        self.user1_mentions = {} #{src: Mention[]}
        self.user2_mentions = {} #{src: Mention[]}

        #These will store all favorites by the target users from the same source
        self.user1_favorites = {} #{src: Favorite[]}
        self.user2_favorites = {} #{src: Favorite[]}
        #These will store all comments by the target users from the same source
        self.user1_comments = {} #{src:Comment[]}
        self.user2_comments = {} #{src:Comment[]}


    def enable_connection_analysis(self):
        self.connection_analysis = True

    def enable_reshare_analysis(self):
        self.reshare_analysis = True

    def enable_mention_analysis(self):
        self.mention_analysis = True

    def enable_favorite_analysis(self):
        self.favortie_analysis = True

    def enable_comment_analysis(self):
        self.comment_analysis = True


    def set_connection(self,nature,source=None,target=None):
        self.connection = nature
        # Only relevant if connection == UNIDIRECTIONAL
        self.conn_source = source
        self.conn_target = target

    def set_common_connections(self,nature,users=None):
        self.common_connections[nature] = users

    def set_connection_path(self,path):
        self.connection_path = path

    def set_reshare(self,user1,user2,posts):
        key = (user1,user2)
        self.reshares[key] = posts

    def set_mention(self,user1,user2,posts):
        key = (user1,user2)
        self.mentions[key] = posts

    def set_favorite(self,user1,user2,posts):
        key = (user1,user2)
        self.favorites[key] = posts

    def set_comment(self,user1,user2,comments):
        key = (user1,user2)
        self.comments[key] = comments

    def set_common_src_reshares(self,user, src,reshares):
        self.common_reshare = True
        reshare_dict = self.user1_reshares if user == self.user1 else self.user2_reshares
        if src not in reshare_dict: # Add key if not already there
            reshare_dict[src] = CommonSrcReshares(self.user1,src)
        # Append the reshare
        reshare_dict[src].set_reshares(reshares)

    def set_common_src_mentions(self,user,src,mentions):
        self.common_mention = True
        mention_dict = self.user1_mentions if user == self.user1 else self.user2_mentions
        mention_dict[src] = mentions

    def set_common_src_favorites(self,user,src,favorites):
        self.common_favorite = True
        favorite_dict = self.user1_favorites if user == self.user1 else self.user2_favorites
        favorite_dict[src] = favorites

    def set_common_src_comments(self,user,src,comments):
        self.common_comment = True
        comment_dict = self.user1_comments if user == self.user1 else self.user2_comments
        comment_dict[src] = comments


    def connection_analysis_format(self):
        """Includes direct and common connections"""
        string_rep = ""
        if self.connection_analysis:
            string_rep += "************* Connection Analysis *************\n"
            string_rep += f"Connection: {self.connection.name}\n"
            if self.connection == 1: #Unidirectional
                string_rep += f"{self.conn_source} follows {self.conn_target}\n"
            string_rep += f"Path: {self.connection_path}"
            string_rep += f"Common Connections:\n"
            if not self.common_connections:
                return string_rep
            for conn_type,users in self.common_connections.items():
                string_rep+= f"{conn_type.name}: \n"
                for user in users:
                    string_rep += f"\t{user}\n"
        return string_rep

    def reshare_analysis_format(self):
        string_rep = ""
        if self.reshare_analysis:
            string_rep += "************* Post Analysis *************\n"
            string_rep += f"Post Sharing: \n"
            string_rep += "" if self.reshares else "NONE\n"
            for key,posts in self.reshares.items():
                user1 = key[0]
                user2 = key[1]
                string_rep += f"{user1} shared the following posts from {user2}: \n"
                for post in posts:
                    original_post = post[0]
                    reshared_post = post[1]
                    string_rep += "Original Post:\n"
                    string_rep+= f"\tid: {original_post.post_id}\n"
                    string_rep += f"\tdate created: {original_post.created_at}\n"
                    string_rep += "\ttext: \n"
                    string_rep += f"\t\t{original_post.get_text()}\n"
                    string_rep += ""
                    string_rep += "Shared Post: \n"
                    string_rep+= f"\tid: {reshared_post.post_id}\n"
                    string_rep += f"\tdate created: {reshared_post.created_at}\n"
                    string_rep += "\ttext: \n"
                    string_rep += f"\t\t{reshared_post.get_text()}\n"
                    string_rep += ""
                    string_rep += "-----------------------------\n"
        return string_rep

    def mention_analysis_format(self):
        string_rep = ""
        if self.mention_analysis:
            string_rep += "************* Mention Analysis *************\n"
            string_rep += f"Direct Mentions: \n"
            string_rep += "" if self.mentions else "NONE\n"
            if not self.mentions:
                return string_rep
            for key,posts in self.mentions.items():
                # Keys are tuples (u1,u2) see set_mention() function
                user1 = key[0]
                user2 = key[1]
                string_rep += f"{user1} mentioned {user2} in these posts: \n"
                for post in posts:
                    string_rep += "Post:\n"
                    string_rep += f"\tid: {post.post_id}\n"
                    string_rep += f"\tdate created: {post.created_at}\n"
                    string_rep += "\ttext: \n"
                    string_rep += f"\t\t{post.get_text()}\n"
                    string_rep += "\n"
                    string_rep += "-----------------------------\n"
        return string_rep

    def favorite_analysis_format(self):
        string_rep = ""
        if self.favortie_analysis:
            string_rep += "************* Likes Analysis *************\n"
            string_rep += f"Direct Likes: \n"
            string_rep += "" if self.favorites else "NONE\n"
            if not self.favorites:
                return string_rep
            for key,posts in self.favorites.items():
                # Keys are tuples (u1,u2) see set_mention() function
                user1 = key[0]
                user2 = key[1]
                string_rep += f"{user1} liked the following posts by  {user2}: \n"
                for post in posts:
                    string_rep += "Post:\n"
                    string_rep += f"\tid: {post.post_id}\n"
                    string_rep += f"\tdate created: {post.created_at}\n"
                    string_rep += "\ttext: \n"
                    string_rep += f"\t\t{post.get_text()}\n"
                    string_rep += "\n"
                    string_rep += "-----------------------------\n"
        return string_rep

    def comment_analysis_format(self):
        string_rep = ""
        if self.comment_analysis:
            string_rep += "************* Comment Analysis *************\n"
            string_rep += f"Direct Comments: \n"
            string_rep += "" if self.comments else "NONE\n"
            for key,comments in self.comments.items():
                user1 = key[0]
                user2 = key[1]
                string_rep += f"{user1} commented on post(s) from {user2}: \n"
                for comment in comments:
                    original_post = comment.post
                    string_rep += "Original Post:\n"
                    string_rep+= f"\tid: {original_post.post_id}\n"
                    string_rep += f"\tdate created: {original_post.created_at}\n"
                    string_rep += "\ttext: \n"
                    string_rep += f"\t\t{original_post.get_text()}\n"
                    string_rep += ""
                    string_rep += "Comment: \n"
                    string_rep += f"\tdate created: {comment.created_at}\n"
                    string_rep += "\ttext: \n"
                    string_rep += f"\t\t{comment.get_text()}\n"
                    string_rep += ""
                    string_rep += "-----------------------------\n"
        return string_rep

    def common_reshare_analysis_format(self):
        string_rep = ""
        if self.common_reshare:
            string_rep += f"Posts shared by {self.user1} and {self.user2} from the same source: \n"
            #For each src, print the src and the tweets of each user
            for src in self.user1_reshares:
                string_rep += f"Both users shared posts from {src}\n"
                for user in [self.user1,self.user2]:
                    user_dict = self.user1_reshares if user == self.user1 else self.user2_reshares
                    string_rep += f"Posts shared by {user}:\n"
                    for reshare in user_dict[src].reshares:

                        original_post = reshare.original_post
                        reshared_post = reshare.reshared_post
                        string_rep += "\tOriginal Post:\n"
                        string_rep += f"\t\tid: {original_post.post_id}\n"
                        string_rep += f"\t\tdate created: {original_post.created_at}\n"
                        string_rep += "\t\ttext: \n"
                        string_rep += f"\t\t\t{original_post.get_text()}\n"
                        string_rep += ""
                        string_rep += "\tShared Post: \n"
                        string_rep += f"\t\tid: {reshared_post.post_id}\n"
                        string_rep += f"\t\tdate created: {reshared_post.created_at}\n"
                        string_rep += "\t\ttext: \n"
                        string_rep += f"\t\t\t{reshared_post.get_text()}\n"
                        string_rep += ""
                string_rep += "-----------------------------\n"
        return string_rep

    def common_mention_analysis_format(self):
        string_rep = ""
        if self.common_mention:
            string_rep += f"Posts in which {self.user1} and {self.user2} mention the same user: \n"
            #For each src, print the src and the tweets of each user
            for src in self.user1_mentions:
                string_rep += f"Both users mentioned {src}\n"
                for user in [self.user1,self.user2]:
                    user_dict = self.user1_mentions if user == self.user1 else self.user2_mentions
                    string_rep += f"Posts made by {user} in which {src} is mentioned:\n"
                    for mention in user_dict[src]:
                        post = mention.post
                        string_rep += "\tPost:\n"
                        string_rep += f"\t\tid: {post.post_id}\n"
                        string_rep += f"\t\tdate created: {post.created_at}\n"
                        string_rep += "\t\ttext: \n"
                        string_rep += f"\t\t\t{post.get_text()}\n"
                        string_rep += "\n"
                string_rep += "-----------------------------\n"

        return string_rep

    def common_favorite_analysis_format(self):
        string_rep = ""
        if self.common_favorite:
            string_rep += f"Posts that {self.user1} and {self.user2} liked that were authored from the same source: \n"
            #For each src, print the src and the tweets of each user
            for src in self.user1_favorites:
                string_rep += f"Both users liked posts from {src}\n"
                for user in [self.user1,self.user2]:
                    user_dict = self.user1_favorites if user == self.user1 else self.user2_favorites
                    string_rep += f"Posts made by {src} that {user} liked:\n"
                    for favorite in user_dict[src]:
                        post = favorite.post
                        string_rep += "\tPost:\n"
                        string_rep += f"\t\tid: {post.post_id}\n"
                        string_rep += f"\t\tdate created: {post.created_at}\n"
                        string_rep += "\t\ttext: \n"
                        string_rep += f"\t\t\t{post.get_text()}\n"
                        string_rep += "\n"
                string_rep += "-----------------------------\n"

        return string_rep

    def common_comment_analysis_format(self):
        string_rep = ""
        if self.common_comment:
            string_rep += f"Users whose posts both {self.user1} and {self.user2} commented on: \n"
            #For each src, print the src and the tweets of each user
            for src in self.user1_comments:
                string_rep += f"Both users commented on posts from {src}\n"
                for user in [self.user1,self.user2]:
                    user_dict = self.user1_comments if user == self.user1 else self.user2_comments
                    string_rep += f"Comments made by {user}:\n"
                    for comment in user_dict[src]:
                        original_post = comment.post
                        string_rep += "\tOriginal Post:\n"
                        string_rep += f"\t\tid: {original_post.post_id}\n"
                        string_rep += f"\t\tdate created: {original_post.created_at}\n"
                        string_rep += "\t\ttext: \n"
                        string_rep += f"\t\t\t{original_post.get_text()}\n"
                        string_rep += ""
                        string_rep += "\tComment: \n"
                        string_rep += f"\t\tdate created: {comment.created_at}\n"
                        string_rep += "\t\ttext: \n"
                        string_rep += f"\t\t\t{comment.get_text()}\n"
                        string_rep += ""
                string_rep += "-----------------------------\n"

        return string_rep

    def print_summary(self):
        print(self.summary_report_format())

    def summary_report_format(self):
        string_rep = "Report Summary\n"
        string_rep += "###############################################################\n"
        if self.connection_analysis:
            string_rep += f"# Connection: {self.connection.name}\n"
            if self.common_connections:
                string_rep += f"#\t{self.user1} and {self.user2} have common connections\n"
            else:
                string_rep += f"#\t{self.user1} and {self.user2} do not have common connections\n"
        if self.reshare_analysis:
            if self.reshares:
                string_rep += "# A reshare relationship was found\n"
                for key in self.reshares:
                    user1 = key[0]
                    user2 = key[1]
                    string_rep += f"#\t{user1} shared at least one post from {user2}\n"
            if self.user1_reshares:
                string_rep +="#\tBoth users shared posts from common sources\n"
        if self.mention_analysis:
            if self.mentions:
                string_rep += "# A mention relationship was found\n"
                for key in self.mentions:
                    user1 = key[0]
                    user2 = key[1]
                    string_rep += f"#\t{user1} mentioned {user2} in at least one post\n"
            if self.user1_mentions:
                string_rep += "#\tBoth users mentioned common source(s) in at least one post\n"
        if self.favortie_analysis:
            if self.favorites:
                string_rep += "# A favorite relationship was found\n"
                for key in self.favorites:
                    user1 = key[0]
                    user2 = key[1]
                    string_rep += f"#\t{user1} liked at least one post by {user2}\n"
            if self.user1_favorites:
                string_rep +="#\tBoth users liked at least one post from common source(s)\n"

        if self.comment_analysis:
            if self.comments:
                string_rep += "# A comment relationship was found\n"
                for key in self.comments:
                    user1 = key[0]
                    user2 = key[1]
                    string_rep += f"#\t{user1} commented on at least one post by {user2}\n"
            if self.user1_comments:
                string_rep += "#\tBoth users commented on  at least one post from common source(s)\n"

        string_rep += "###############################################################\n"
        return string_rep







# TODO: Print summary report
    def __repr__(self):
        string_rep = f"User1: {self.user1}\nUser2: {self.user2}\n"
        ################## Connection analysis section ##########################
        string_rep += self.connection_analysis_format()
        ################## Post analysis section ##########################
        ###### Reshares #######
        string_rep += self.reshare_analysis_format()
        string_rep += self.common_reshare_analysis_format()
        ###### Mentions #######
        string_rep += self.mention_analysis_format()
        string_rep += self.common_mention_analysis_format()
        ###### Favorites #######
        string_rep += self.favorite_analysis_format()
        string_rep += self.common_favorite_analysis_format()
        ###### Comments #######
        string_rep += self.comment_analysis_format()
        string_rep += self.common_comment_analysis_format()

        return string_rep


######################### HELPER CLASSES #############################
class CommonSrcReshares():
    def __init__(self,user,src=None,reshares=None):
        self.user = user
        self.src = src
        self.reshares = reshares

    def set_reshares(self,reshares):
        self.reshares = reshares
        # if not self.reshares:
        #     self.reshares = []
        # self.reshares.append(reshare)

    def __repr__(self):
        return f"CommonReshare({self.src}:{self.reshares})"


############################ ENUMS ###################################

class Connection(Enum):
    BIDIRECTIONAL = 0
    UNIDIRECTIONAL = 1
    NONE = 2

class CommonConnections(Enum):
    COMMON_FRIENDS = 0
    COMMON_FOLLOWERS = 1
    NO_COMMON_CONNECTIONS = 2








