import discord
from discord.ext import commands
import random
import json
import functools
import os

json_location = os.path.join(os.getcwd(),'resources', 'candy_collection.json')


class CandyCollection:
    def __init__(self, bot):
        self.bot = bot
        with open(json_location) as candy:
            self.candy_json = json.load(candy)
            self.msg_reacted = self.candy_json['msg_reacted']
        self.get_candyinfo = dict()
        for userinfo in self.candy_json['records']:
            userid = userinfo['userid']
            self.get_candyinfo[userid] = userinfo

    HACKTOBER_CHANNEL_ID = 496432022961520650
    # chance is 1 in x range, so 1 in 20 range would give 5% chance (for add candy)
    ADD_CANDY_REACTION_CHANCE = 20  # 5%
    ADD_CANDY_EXISTING_REACTION_CHANCE = 10  # 10%
    ADD_SKULL_REACTION_CHANCE = 50  # 2%
    ADD_SKULL_EXISTING_REACTION_CHANCE = 20  # 5%

    async def on_message(self, message):
        """Make sure the user is not a bot and
            the channel is #event-hacktoberfest.
            Because the skull has a lower chance of occurring
            we'll check for that first, and then add respective reactions"""
        if message.author.bot:
            return
        if message.channel.id != self.HACKTOBER_CHANNEL_ID:
            return
        if random.randint(1, self.ADD_SKULL_REACTION_CHANCE) == 1:
            d = {"reaction": '\N{SKULL}', "msg_id": message.id, "won": False}
            self.msg_reacted.append(d)
            return await message.add_reaction('\N{SKULL}')
        if random.randint(1, self.ADD_CANDY_REACTION_CHANCE) == 1:
            d = {"reaction": '\N{CANDY}', "msg_id": message.id, "won": False}
            self.msg_reacted.append(d)
            return await message.add_reaction('\N{CANDY}')

    async def on_reaction_add(self, reaction, user):
        """Make sure the reaction is in #event-hacktoberfest
            and the user reacting is not a bot (ie. ourselves)
            Check if the reaction is a skull/candy first. """
        message = reaction.message
        if message.channel.id != self.HACKTOBER_CHANNEL_ID:
            return
        if user.bot:
            return
        if str(reaction.emoji) not in ('\N{SKULL}', '\N{CANDY}'):
            if message.id in await self.ten_recent_msg():
                await self.reacted_msg_chance(message)
            return
        for react in self.msg_reacted:
            # check to see if the message id of a message we added a
            # reaction to is in json file, and if nobody has won/claimed it yet
            if react['msg_id'] == message.id and react['won'] is False:
                react['user_reacted'] = user.id
                react['won'] = True
                try:
                    # if they have record/candies in json already it will do this
                    user_records = self.get_candyinfo[user.id]
                    if str(reaction.emoji) == '\N{CANDY}':
                        user_records['record'] += 1
                    if str(reaction.emoji) == '\N{SKULL}':
                        if user_records['record'] <= 3:
                            user_records['record'] = 0
                            lost = 'all of your'
                        else:
                            lost = random.randint(1, 3)
                            user_records['record'] -= lost
                        await self.send_spook_msg(message.channel, lost)

                except KeyError:
                    # otherwise it will raise KeyError so we need to add them
                    if str(reaction.emoji) == '\N{CANDY}':
                        print('ok')
                        d = {"userid": user.id, "record": 1}
                        self.candy_json['records'].append(d)
                await self.remove_reactions(reaction)

    async def reacted_msg_chance(self, message):
        """(Randomly) add a skull or candy to a message if there is a reaction there already
             (higher probability)"""
        if random.randint(1, self.ADD_SKULL_EXISTING_REACTION_CHANCE) == 1:
            d = {"reaction": '\N{SKULL}', "msg_id": message.id, "won": False}
            self.msg_reacted.append(d)
            return await message.add_reaction('\N{SKULL}')

        if random.randint(1, self.ADD_CANDY_EXISTING_REACTION_CHANCE) == 1:
            d = {"reaction": '\N{CANDY}', "msg_id": message.id, "won": False}
            self.msg_reacted.append(d)
            return await message.add_reaction('\N{CANDY}')

    async def ten_recent_msg(self):
        """Get the last 10 messages sent in the channel"""
        ten_recent = []
        recent_msg = max((x for x in self.bot._connection._messages
                          if x.channel.id == self.HACKTOBER_CHANNEL_ID), key=lambda x: x.id)
        channel = await self.hacktober_channel()
        ten_recent.append(recent_msg.id)
        for i in range(9):
            o = discord.Object(id=recent_msg.id + i)
            msg = await channel.history(limit=1, before=o).next()
            ten_recent.append(msg.id)
        return ten_recent

    async def get_message(self, msg_id):
        """Get the message from it's ID. Use history rather than get_message due to
        poor ratelimit (50/1s vs 1/1s)"""
        try:
            o = discord.Object(id=msg_id + 1)
            msg = await self.hacktober_channel.history(limit=1, before=o).next()
            if msg.id != msg_id:
                return None
            return msg
        except Exception:
            return None

    async def hacktober_channel(self):
        """Get #events-hacktober channel from it's id"""
        return self.bot.get_channel(id=self.HACKTOBER_CHANNEL_ID)

    async def remove_reactions(self, reaction):
        """Remove all candy/skull reactions"""
        try:
            async for user in reaction.users():
                await reaction.message.remove_reaction(reaction.emoji, user)
        except discord.HTTPException:
            pass

    async def send_spook_msg(self, channel, candies):
        """Send a (lame) spooky message"""
        e = discord.Embed(colour=discord.Member.colour)
        e.set_author(name="You went to bed last night and the witch visited your grave."
                          " She left a message that you will be cursed for as long as you live."
                          f" You woke up this morning and found that {candies} candies had disappeared")
        await channel.send(embed=e)

    def save_to_json(self):
        """Save json to the file. We will do this with bad practice
         async (run_in_executor) to prevent blocking"""
        with open(json_location, 'w') as outfile:
            json.dump(self.candy_json, outfile)

    @commands.command()
    async def candy(self, ctx):
        """Get the candy leaderboard and save to json when this is called"""
        thing = functools.partial(self.save_to_json)
        save = await self.bot.loop.run_in_executor(None, thing)
        emoji = (
            '\N{FIRST PLACE MEDAL}',
            '\N{SECOND PLACE MEDAL}',
            '\N{THIRD PLACE MEDAL}',
            '\N{SPORTS MEDAL}',
            '\N{SPORTS MEDAL}'
        )
        top_sorted = sorted(self.candy_json['records'], key=lambda k: k.get('record', 0), reverse=True)
        top_five = top_sorted[:5]
        usersid = []
        records = []
        for record in top_five:
            usersid.append(record['userid'])
            records.append(record['record'])

        value = '\n'.join(f'{emoji[index]} <@{usersid[index]}>: {records[index]}'
                          for index in range(0, len(usersid))) or 'No Candies'
        e = discord.Embed(colour=discord.Colour.blurple())
        e.add_field(name="Top Candy Records", value=value, inline=False)
        e.add_field(name='\u200b',
                    value=f"Candies will randomly appear on messages sent. "
                          f"\nHit the candy when it appears as fast as possible to get the candy! "
                          f"\nBut beware the witch...",
                    inline=False)
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(CandyCollection(bot))
