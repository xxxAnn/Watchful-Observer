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

    async def handle_command(self, message: discord.Message):
        if message.content.startswith("!messages"):
            await message.channel.send(f"Currently stored {len(self.user_stats.tracked_messages)} messages from {len(self.user_stats.users)} users.", reference=message)

    async def on_message(self, message: discord.Message):

        if  message.content.startswith("!"): await self.handle_command(message)

        self.user_stats.add_message(await MessageData.from_message(message), message.author.id)

    
    async def analyze_channel(self, channel: discord.TextChannel):
        i = 0
        async for msg in channel.history(limit=None, before=discord.Object(self.user_stats.tracked_messages[0])):
            self.user_stats._raw_on_message(await MessageData.from_message(msg), msg.author.id)
            i = (i+1) % 100
            if i == 1:
                self.user_stats.save()


    async def on_ready(self):
        self.tree.copy_global_to(guild=discord.Object(776251117616234506))

        await self.analyze_channel(await self.fetch_channel(1148075747118960774))
        await self.tree.sync()

        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='Group Chat Extended'))

class UserStats:
    
    def __init__(self, tracked_messages, users, tracking_since):
        self.tracking_since = tracking_since
        # sorted list
        self.tracked_messages = tracked_messages
        self.users = users

    def _raw_on_message(self, data, author_id):
        if self.__binary_tree_insert(data.id):
            self.add_message_to_user(author_id, data)
            return True
        return False

    def add_message(self, data, author_id):
        if self._raw_on_message(data, author_id):
            self.save()


    def add_message_to_user(self, author_id, data):
        usr = self.users.get(author_id, UserProfile([]))

        usr.add_message(data)

        self.users[author_id] = usr

    def save(self):
        j = json.dumps(self.into_json(), indent=4)
        open('userstats.json', 'w', encoding='utf-8').write(j)
    
    def __binary_tree_insert(self, id):
        l,h=0,len(self.tracked_messages)
        while h > (m:=(l+h)//2) >= l:
            oid = self.tracked_messages[m]
            if id>oid:l=m+1
            elif id<oid:h=m-1
            else: return False

        if m==len(self.tracked_messages):
            self.tracked_messages.append(id)
        elif self.tracked_messages[m] > id:
            self.tracked_messages.insert(m, id)
        else:
            self.tracked_messages.insert(m+1, id)
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
        return {'messages': list(map(MessageData.into_json, self.messages))}

class MessageData:

    def __init__(self, id, content, attch_links, reactions, channel_id=None):
        self.id = id
        self.content = content
        self.attch_links = attch_links
        self.channel_id = channel_id
        self.reactions = reactions

    @classmethod
    def from_json(cls, obj):
        return MessageData(int(obj['id']), obj['content'], obj['attachment_links'], list(map(ReactionData.from_json, obj['reactions'])), int(obj['channel_id']))
    
    @classmethod
    async def from_message(cls, msg: discord.Message):
        return MessageData(msg.id, msg.content, [a.url for a in msg.attachments], [await ReactionData.from_reaction(reaction) for reaction in msg.reactions], msg.channel.id)
    
    def into_json(self):
        return {'id': str(self.id), 'content': self.content, 'attachment_links': self.attch_links, 'channel_id': str(self.channel_id), 'reactions': list(map(ReactionData.into_json, self.reactions))}
    
class ReactionData:

    def __init__(self, emoji, users):
        self.emoji = emoji
        self.users = users

    @classmethod
    async def from_reaction(cls, reaction: discord.Reaction):
        return ReactionData(str(reaction.emoji),  [user.id async for user in reaction.users()])

    @classmethod
    def from_json(cls, obj):
        return ReactionData(obj['emoji'], list(map(int, obj['users'])))
    
    def into_json(self):
        return {'emoji': self.emoji, 'users': self.users}
    
if __name__ == '__main__':
    intents = discord.Intents.default()
    intents.message_content = True
    u = UserStats.from_json(json.loads(open('userstats.json', 'r', encoding='utf-8').read()))
    client = WatchfulEye(u, intents=intents)
    tree = discord.app_commands.CommandTree(client)

    client.set_tree(tree)

    client.run(os.environ.get("WATCHFULEYE"))

