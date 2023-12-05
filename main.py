import discord
import json
import os

class WatchfulEye(discord.Client):
    def __init__(self, user_stats, *args, **kwargs):
        self.user_stats = user_stats
        self.can_start = False

        super().__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        if self.can_start:
            super().run(*args, **kwargs)
        # error otherwise

    def set_tree(self, tree):
        self.tree = tree
        self.can_start = True

    async def on_message(self, message: discord.Message):
        
        self.user_stats.add_message(message)

    async def on_ready(self):
        self.tree.copy_global_to(guild=discord.Object(776251117616234506))

        await self.tree.sync()

        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='Group Chat Extended'))


        print('Logged in as', self.user)

class UserStats:
    
    def __init__(self, tracked_messages, users, tracking_since):
        self.tracking_since = tracking_since
        # sorted list
        self.tracked_messages = tracked_messages
        self.users = users
        print(self.users)

    def add_message(self, msg: discord.Message):
        data = MessageData.from_message(msg)
        if self.__binary_tree_insert(data.id):
            self.add_message_to_user(msg.author.id, data)
            self.save()


    def add_message_to_user(self, author_id, data):
        usr = self.users.get(author_id, UserProfile([]))

        usr.add_message(data)

        self.users[author_id] = usr

    def save(self):
        j = json.dumps(self.into_json(), indent=4)
        open('userstats.json', 'w').write(j)
    
    def __binary_tree_insert(self, id):
        # O(n)
        l,h=0,len(self.tracked_messages)
        while h > (m:=(l+h)//2) >= l:
            oid = self.tracked_messages[m]
            if id>oid:l=m+1
            elif id<oid:h=m-1
            else: return False

        self.tracked_messages.insert(m, id)
        return True

    @classmethod
    def from_json(cls, obj):
        l = {}
        for k, usr in obj['users'].items():
            l[int(k)] = UserProfile.from_json(usr)

        tracking_since = obj['tracking_since']
        tracked_messages = list(map(int, obj['tracked_messages']))

        return UserStats(tracked_messages, l, tracking_since)
    
    def into_json(self):
        return {'tracking_since': self.tracking_since, 'tracked_messages': list(map(str, self.tracked_messages)), 'users': {str(k): u.into_json() for k, u in self.users.items()}}


class UserProfile:
    
    def __init__(self, messages):
        self.messages = messages

    def add_message(self, data):
        self.messages.append(data)

    @classmethod
    def from_json(cls, obj):
        l = []
        for msg in obj['messages']:
            l.append(MessageData.from_json(msg))

        return UserProfile(l)
    
    def into_json(self):
        return {'messages': [m.into_json() for m in self.messages]}

class MessageData:

    def __init__(self, id, content, attch_links, channel_id=None):
        self.id = id
        self.content = content
        self.attch_links = attch_links
        self.channel_id = channel_id

    @classmethod
    def from_json(cls, obj):
        return MessageData(int(obj['id']), obj['content'], obj['attachment_links'], int(obj['channel_id']))
    
    @classmethod
    def from_message(cls, msg: discord.Message):
        return MessageData(msg.id, msg.content, [a.url for a in msg.attachments], msg.channel.id)
    
    def into_json(self):
        return {'id': str(self.id), 'content': self.content, 'attachment_links': self.attch_links, 'channel_id': str(self.channel_id)}
    


if __name__ == '__main__':
    intents = discord.Intents.default()
    intents.message_content = True
    u = UserStats.from_json(json.loads(open('userstats.json', 'r').read()))
    client = WatchfulEye(u, intents=intents)
    tree = discord.app_commands.CommandTree(client)

    client.set_tree(tree)

    client.run(os.environ.get("WATCHFULEYE-TEST"))

