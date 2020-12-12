from discord.ext import commands

from settings import get_global_state, get_categories, get_subcategories, get_tournaments
from utils import dictionary_to_embed
from utils import inverse_dictionary_to_embed


def setup(bot):
    print('help module successfully reloaded')
    bot.add_cog(HelpCog(bot))

class HelpCog(commands.Cog):

    @commands.command()
    async def categories(self, ctx, *args):
        state = get_global_state()
        state.skip_message = ctx.message
        await ctx.send(embed=inverse_dictionary_to_embed('Categories', get_categories(), ctx))

    @commands.command()
    async def subcategories(self, ctx, *args):
        state = get_global_state()
        state.skip_message = ctx.message
        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        # note: Embeds have a max of 25 fields, and there are far more than 25 subcategories
        for chunk in chunks(list(get_subcategories().items()), 25):
            await ctx.send(embed=inverse_dictionary_to_embed('Subcategories', dict(chunk), ctx))

    @commands.command()
    async def tournaments(self, ctx, *args):
        state = get_global_state()
        state.skip_message = ctx.message
        await ctx.send(embed=dictionary_to_embed('Tournaments', get_tournaments(), ctx))