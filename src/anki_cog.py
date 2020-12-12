from discord.ext import commands

def setup(bot):
    print('anki module successfully reloaded')
    bot.add_cog(AnkiCog(bot))

class AnkiCog(commands.Cog):

    pass