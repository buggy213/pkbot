from discord.ext import commands

def setup(bot):
    print('stats module successfully reloaded')
    bot.add_cog(StatsCog(bot))

class StatsCog(commands.Cog):
    @commands.command()
    def personalstats(self, ctx, *args):
        if len(args) == 0:
            title = "Cumulative"
        else:
            if args[0] == 'category':
                pass
            if args[0] == 'difficulty':
                pass