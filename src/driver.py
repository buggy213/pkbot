import pprint
from collections import namedtuple

from discord.ext import commands

from database import get_pkbot_session
from settings import get_global_state
from utils import code_block, dictionary_to_embed


class SessionState:
    # Should return dictionary
    def stats(self):
        return dict()

# For now we'll only have 1 session per user - tbh this makes the most sense anyways
def get_session(author, session_type=None):
    state = get_global_state()
    session = [session for session in state.sessions if session.context.author == author]
    if session_type is not None:
        session = list(filter(lambda x: isinstance(x.session_state, session_type), session))
    assert len(session) < 2
    if len(session) == 0:
        return None
    return session[0]

def load_extensions(bot):
    for ext in extensions:
        bot.load_extension(ext)

def unload_extensions(bot):
    for ext in extensions:
        bot.unload_extension(ext)

def reload_extensions(bot):
    for ext in extensions:
        bot.reload_extension(ext)

client = commands.Bot(command_prefix=commands.when_mentioned_or('.', '^'))
extensions = ['pk_cog', 'tk_cog', 'help_cog', 'anki_cog']
Session = namedtuple('Session', 'context,command,session_state')

@client.event
async def on_message(message):
    await client.process_commands(message)

@client.command()
async def reloadcogs(ctx):
    reload_extensions(client)

@client.command()
async def getloadedcogs(ctx):
    await ctx.send(code_block(pprint.pformat(client.extensions)))

@client.command()
async def end(ctx):
    state = get_global_state()
    state.skip_message = ctx.message

    # Don't end what a different cog is doing
    session = get_session(ctx.author)
    if session is not None:
        await stats(ctx)
        state.sessions.remove(session)

pkbot_session = get_pkbot_session()

@client.command()
async def stats(ctx):
    get_global_state().skip_message = ctx.message
    session = get_session(ctx.author)
    if session is not None:
        stats_dictionary, session_to_db_fn = session.session_state.stats()
        msg = dictionary_to_embed('Stats', stats_dictionary, ctx)
        msg.add_field(name='Settings', value=str(session.command))
        await ctx.send(embed=msg)
        if session_to_db_fn is not None:
            db_object = session_to_db_fn(stats_dictionary, session)
            pkbot_session.add(db_object)
            pkbot_session.commit()


if __name__ == '__main__':
    load_extensions(client)
    try:
        with open('token') as f:
            client.run(f.read())
    except FileNotFoundError:
        print('Cannot find client token, stopping')