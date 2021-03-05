import discord 
from discord.ext import commands 

import os 
import sys 

import json 
import sqlite3 

import requests 
import asyncio 

import colorama 
from colorama import init, Fore

#################################################

token = "bot token goes here"

#################################################

class Database:
    def __init__(self):
        self._conn = sqlite3.connect('Database/Data.db')
        self._c = self._conn.cursor()

    def remove_guild(self, server_id: int):
        if self.check_guild(server_id) == 0:
            return
        self._c.execute(f"DELETE FROM guilds WHERE server_id={int(server_id)}") 
        self._conn.commit()
        return 

    def check_guild(self, server_id: int):
        self._c.execute(f"SELECT prefix FROM guilds WHERE server_id={int(server_id)}")
        r = self._c.fetchone()
        if r is None or r == None:
            return 0
        return 1

    def check_user(self, server_id: int, user_id: int):
        self._c.execute(f"SELECT whitelisted FROM database WHERE server_id={int(server_id)} AND user_id={int(user_id)}")
        r = self._c.fetchone()
        if r is None or r == None:
            return 0
        return 1

    def get_prefix(self, server_id: int):
        self._c.execute(f"SELECT prefix FROM guilds WHERE server_id={int(server_id)}")
        r = self._c.fetchone()
        if r is None or r == None:
            self.add_guild(server_id)
            return "ai?"
        result = r[0]
        return result 

    def change_prefix(self, server_id: int, prefix: str):
        if self.check_guild(server_id) == 1:
            self._c.execute(f'UPDATE guilds SET prefix="{prefix}" WHERE server_id={int(server_id)}')
            self._conn.commit()
            return 
        self.add_guild(server_id)
        self._c.execute(f'UPDATE guilds SET prefix="{prefix}" WHERE server_id={int(server_id)}')
        self._conn.commit()
        return


    def add_guild(self, server_id: int):
        self._c.execute("INSERT INTO guilds VALUES (?, ?)", (server_id, "ai?"))
        self._conn.commit()
        return

    def add_user(self, server_id: int, user_id: int):
        self._c.execute("INSERT INTO database VALUES (?, ?, ?)", (server_id, user_id, 0))
        self._conn.commit()
        return True

    def is_whitelisted(self, server_id: int, user_id: int):
        self._c.execute(f"SELECT whitelisted FROM database WHERE server_id={int(server_id)} AND user_id={int(user_id)}")
        r = self._c.fetchone()
        if r is None or r == None:
            self.add_user(server_id, user_id)
            return 0 
        result = r[0]
        if result == 0:
            return 0 
        return result

    def whitelist(self, server_id: int, user_id: int):
        if self.check_user(server_id, user_id) == 0:
            self.add_user(server_id, user_id)
            self._c.execute(f"UPDATE database SET whitelisted=1 WHERE server_id={int(server_id)} AND user_id={int(user_id)}")
            self._conn.commit()
            return True

        self._c.execute(f"UPDATE database SET whitelisted=1 WHERE server_id={int(server_id)} AND user_id={int(user_id)}")
        self._conn.commit()
        return True

    def remove_whitelist(self, server_id: int, user_id: int):
        if self.check_user(server_id, user_id) == 0:
            self.add_user(server_id, user_id)
        
        self._c.execute(f"UPDATE database SET whitelisted=0 WHERE server_id={int(server_id)} AND user_id={int(user_id)}")
        self._conn.commit()
        return


d = Database()

#################################################

def get_prefix(bot, message):
    prefix = d.get_prefix(message.guild.id)
    return prefix

bot = commands.Bot(command_prefix=get_prefix)

#################################################

@bot.event 
async def on_guild_join(guild):
    d.add_guild(guild.id)

@bot.event 
async def on_guild_remove(guild):
    d.remove_guild(guild.id)

#################################################

@bot.event 
async def on_ready():
    print(f'    {Fore.YELLOW}.$ Bot Ready')

@bot.event 
async def on_message(msg):
    if msg.guild:
        if msg.content == f'<@!{bot.user.id}>' or msg.content == f'<@{bot.user.id}>':
            prefix = d.get_prefix(msg.guild.id)

            embed = discord.Embed(
                title = f'{msg.guild.name}\'s Prefix: ',
                description = f'```{prefix}```'
            )

            await msg.channel.send(embed=embed)
            return 
        if 'discord.gg/' in msg.content:
            if msg.author.guild_permissions.administrator:
                return 

            if d.is_whitelisted(msg.guild.id, msg.author.id) == 1:
                return 
                
                
            await msg.delete()
            print(f'    {Fore.YELLOW}.$ {Fore.LIGHTRED_EX}Invite Detected - {msg.author.name} - {msg.guild.name}')
            return 

        await bot.process_commands(msg)    

#################################################

@bot.command()
async def whitelist(ctx):
    pass

@bot.command()
async def add_whitelist(ctx, member: discord.Member=None):
    if member is None:
        embed = discord.Embed(
            color = discord.Color.red()
        )
        embed.add_field(name="Error", value="You didn't specified any users to add to the whitelist")

        await ctx.send(embed=embed)
        return 
    
    if ctx.author.guild_permissions.administrator:
        if d.whitelist(ctx.guild.id, member.id):
            embed = discord.Embed(
                title = "Succes",
                description = f"We've added {member.mention} to the whitelist"
            )

            await ctx.send(embed=embed)
            return 

@bot.command()
async def remove_whitelist(ctx, member: discord.Member=None):
    if member is None:
        embed = discord.Embed(
            color = discord.Color.red()
        )
        embed.add_field(name="Error", value="You didn't specified any users to add to remove from the whitelist")

        await ctx.send(embed=embed)
        return 
        
    if ctx.author.guild_permissions.administrator:
        d.remove_whitelist(ctx.guild.id, member.id)

        embed = discord.Embed(
            title = "Succes",
            description = f"We've removed {member.mention} from the whitelist"
        )

        await ctx.send(embed=embed)
        return 
    

#################################################

@bot.command()
async def prefix(ctx):
    prefix = d.get_prefix(ctx.guild.id)

    embed = discord.Embed(
        title = f'Prefix Command',
        description = f'`{prefix}change_prefix <new prefix>`'
    )
    embed.set_footer(text=f"Prefix: {prefix}", icon_url=ctx.author.avatar_url)

    await ctx.send(embed=embed)

@bot.command()
async def change_prefix(ctx, prefix: str):
    if len(prefix) > 5:
        embed = discord.Embed(
            color = discord.Color.red()
        )
        embed.add_field(name="Error", value="The len of the prefix can't be more than 5")

        await ctx.send(embed=embed)
        return
    if ctx.author.guild_permissions.administrator:
        d.change_prefix(ctx.guild.id, prefix)

        embed = discord.Embed(
            color = discord.Color.green()
        )
        embed.add_field(name="Succes", value=f"The new prefix for this server is now: `{prefix}`")
        await ctx.send(embed=embed)

#################################################

bot.run(token)