from discord.ext import commands, tasks
from sqlalchemy import func

from database import get_quizdb_session, Tossup, Tournament, TkSession
from driver import SessionState, Session, get_session
from settings import parse_arguments, get_global_state
from collections import defaultdict
from utils import html_to_discord, hyperlink, get_wikipedia_search
from answer_validator import validate, Correctness

import discord
import re
import asyncio

def setup(bot):
    bot.add_cog(TkCog(bot))
    print('tk module successfully reloaded')

def session_to_db_object(stats, session):
    return TkSession(discord_user=session[0].author.id, tossups_heard=str(stats['Tossups Heard']),
                     tens=str(stats['Tens']), powers=str(stats['Powers']), negs=str(stats['Incorrect']),
                     points=str(stats['Points']), settings=str(session[1]))

class TkSessionState(SessionState):
    def __init__(self):
        self.user_stats = defaultdict(lambda: defaultdict(int)) # number of tossups heard, answered, powered, negged, amount of time for each user
        self.tossups = []
        self.current_tossup = None
        self.current_message = None
        self.position = 0 # position in tossup
        self.read_speed = 5 # words or word equivalents / loop
        self.prompting = False
        self.lockout = None
        self.multiple_buzzes = False
        self.game = False # can multiple users play simultaneously


    def stats(self):
        if self.game:
            # TODO: implement multi-player
            pass
        else:
            if len(self.user_stats.values()) == 0:
                self.user_stats['dummy'] = ({'tossups_heard': 0,
                                            'tens': 0,
                                            'powers': 0,
                                            'incorrect': 0,
                                            }, None)

            player = list(self.user_stats.values())[0]
            return ({
                "Tossups Heard": player['tossups_heard'],
                "Tens": player['tens'],
                "Powers": player['powers'],
                "Incorrect": player['incorrect'],
                "Points": player['tens'] * 10 + player['powers'] * 15 + player['incorrect'] * -5,
                "PPTUH": (player['tens'] * 10 + player['powers'] * 15 + player['incorrect'] * -5) / player['tossups_heard'] \
                    if player['tossups_heard'] != 0 else 'N/A'
            },
            session_to_db_object
            )
class TkCog(commands.Cog):
    def get_tossup_batch(self, arguments, batch_size=20):
        if not hasattr(self, 'db_session'):
            # initialize ourselves a session into db
            self.db_session = get_quizdb_session()
        difficulties, categories, subcategories, selected_tournaments = parse_arguments(arguments)

        # Big expression here filters for bonuses that match difficulty, category, subcategory, and tournament
        tossups = self.db_session.query(Tossup)
        if len(categories) > 0:
            tossups = tossups.filter(Tossup.category_id.in_(categories))
        if len(subcategories) > 0:
            tossups = tossups.filter(Tossup.subcategory_id.in_(subcategories))
        if len(selected_tournaments) > 0:
            tossups = tossups.filter(Tossup.tournament_id.in_(selected_tournaments))
        if len(difficulties) > 0:
            tossups = tossups.join(Tournament).filter(Tournament.difficulty.in_(difficulties))
        tossups = tossups.order_by(func.random()).limit(batch_size)
        print(str(tossups)) # print out SQL statement
        output = list()
        for tossup in tossups:
            output.append((tossup, tossup.tournament))

        return output

    async def load_tossup(self, session):
        # checks if new tossups are needed, then puts another into 'current_tossup'
        if len(session.session_state.tossups) <= 1:
            tossup_batch = self.get_tossup_batch(session.command)
            if len(tossup_batch) == 0:
                await session.context.send('Search returned 0 results -- ending tk')
                await end(session.context)
                return False
            session.session_state.tossups.extend(tossup_batch)
        session.session_state.current_tossup = session.session_state.tossups.pop()
        return True

    @commands.command()
    async def tk(self, ctx, *args):
        state = get_global_state()
        state.skip_message = ctx.message
        if all([ctx.author != session.context.author for session in state.sessions]):
            new_session = Session(ctx, args, TkSessionState())
            state.sessions.append(new_session)
            await self.read_tossup(ctx, new_session)
        else:
            await ctx.send(f'{ctx.author} is already in a session')

    # Fixes "unmatched" asterisks and underlines caused by splitting markdown
    def fix_markdown(self, text):
        asterisks = re.findall(r'\*{2,}', text)
        underlines = re.findall(r'_{2,}', text)
        if len(asterisks) % 2 == 1 and len(underlines) % 2 == 1:
            if asterisks[-1].start() < underlines[-1].start():
                text += '_' * len(underlines[-1])
                text += '*' * len(asterisks[-1])
            else:
                text += '*' * len(asterisks[-1])
                text += '_' * len(underlines[-1])
        elif len(asterisks) % 2 == 1:
            text += '*' * len(asterisks[-1])
        elif len(underlines) % 2 == 1:
            text += '_' * len(underlines[-1])
        return text

    def create_tossup_embed(self, tossup_markdown, session):
        state = session.session_state
        tossup_markdown = self.fix_markdown(' '.join(tossup_markdown.split(' ')[:state.position]))
        tossup = discord.Embed(color=0x00ff00)
        if len(tossup_markdown) > 1000:
            # Shouldn't ever need three fields
            tossup.add_field(name=f'{state.current_tossup[1].name}',
                             value=f'{tossup_markdown[:1000]}')
            tossup.add_field(name='cont', value=f'{tossup_markdown[1000:]}')
        else:
            tossup.add_field(name=f'{state.current_tossup[1].name}',
                         value=f'{tossup_markdown}')
        tossup.set_author(name=f' for {session.context.author.display_name}',
                          icon_url=session.context.author.avatar_url)
        return tossup

    async def read_tossup(self, ctx, session, delay=2):
        self.read_loop.cancel()
        session.session_state.position = 0
        if delay != 0:
            await asyncio.sleep(delay)
        if await self.load_tossup(session):
            await self.start_read(ctx, html_to_discord(session.session_state.current_tossup[0].formatted_text),
                        session)
    async def start_read(self, ctx, tossup_markdown, session):
        state = session.session_state
        state.position += state.read_speed
        state.current_message = await ctx.send(embed=self.create_tossup_embed(tossup_markdown, session))
        self.read_loop.start(tossup_markdown, session)

    @tasks.loop(seconds=1.0)
    async def read_loop(self, tossup_markdown, session):
        state = session.session_state
        state.position += state.read_speed
        await state.current_message.edit(embed=self.create_tossup_embed(tossup_markdown, session))

    @commands.Cog.listener()
    async def on_message(self, message):
        if get_global_state().skip_message is not None and message.id == get_global_state().skip_message.id:
            # skip it, it was used for a bot command
            return
        if message.content.startswith('_'):
            # skip skip
            return
        def check_power(session):
            tossup_markdown = html_to_discord(session.session_state.current_tossup[0].formatted_text)
            return self.fix_markdown(' '.join(tossup_markdown.split(' ')[:session.session_state.position])).endswith('**')

        session = get_session(message.author, TkSessionState)
        if session is not None:
            if session.session_state.prompting:
                session.session_state.prompting = False
                if message.content.lower().startswith('y'):
                    if check_power(session):
                        session.session_state.user_stats[message.author.id]['points'] += 15
                        session.session_state.user_stats[message.author.id]['powers'] += 1
                    else:
                        session.session_state.user_stats[message.author.id]['points'] += 10
                        session.session_state.user_stats[message.author.id]['tens'] += 1
                else:
                    session.session_state.user_stats[message.author.id]['incorrect'] += 1
                session.session_state.user_stats[message.author.id]['tossups_heard'] += 1
                await self.read_tossup(session.context, session, delay=2)
            else:
                if session.session_state.lockout is not None:
                    session.session_state.lockout = None
                else:
                    session.session_state.lockout = message
                    self.read_loop.cancel()
                    buzz_notification = discord.Embed(color=0xff00ff)
                    buzz_notification.set_author(name=f'{session.context.author.display_name}',
                                             icon_url=session.context.author.avatar_url)
                    buzz_notification.add_field(name='Buzz', value=f'goes to {session.context.author.display_name}')
                    await session.context.send(embed=buzz_notification)
                    return

                given_answer = message.content
                answerline = session.session_state.current_tossup[0].formatted_answer
                correctness, formatted_answer, main_answer, unformatted_main_answer, correct_answers = validate(
                    given_answer, answerline)

                if correctness == Correctness.INCORRECT:
                    session.session_state.user_stats[message.author.id]['incorrect'] += 1
                    session.session_state.user_stats[message.author.id]['tossups_heard'] += 1
                    # break out early - definitely not the answer
                    incorrect_msg = discord.Embed(color=0xff0000)
                    wiki_search = hyperlink(html_to_discord(formatted_answer),
                                            get_wikipedia_search(unformatted_main_answer))
                    incorrect_msg.add_field(name='Sorry, incorrect', value=wiki_search)
                    incorrect_msg.set_author(name=f' for {session.context.author.display_name}',
                                             icon_url=session.context.author.avatar_url)
                    await message.channel.send(embed=incorrect_msg)
                    await self.read_tossup(session.context, session, delay=2)
                elif correctness == Correctness.CORRECT:
                    if check_power(session):
                        session.session_state.user_stats[message.author.id]['points'] += 15
                        session.session_state.user_stats[message.author.id]['powers'] += 1
                    else:
                        session.session_state.user_stats[message.author.id]['points'] += 10
                        session.session_state.user_stats[message.author.id]['tens'] += 1
                    session.session_state.user_stats[message.author.id]['tossups_heard'] += 1
                    correct_msg = discord.Embed(color=0x0000ff)
                    wiki_search = hyperlink(html_to_discord(formatted_answer),
                                            get_wikipedia_search(unformatted_main_answer))
                    correct_msg.add_field(name='Correct', value=wiki_search)
                    correct_msg.set_author(name=f' for {session.context.author.display_name}',
                                           icon_url=session.context.author.avatar_url)
                    await message.channel.send(embed=correct_msg)
                    await self.read_tossup(session.context, session, delay=2)
                else:
                    session.session_state.prompting = True
                    # await message.channel.send(
                    #    f'DEBUG: correct_answers = {correct_answers}, similarities = {[fuzz.ratio(ans.lower(), given_answer.lower()) for ans in correct_answers]}')
                    prompt_msg = discord.Embed(color=0xff0000)
                    wiki_search = hyperlink(html_to_discord(formatted_answer),
                                            get_wikipedia_search(unformatted_main_answer))
                    prompt_msg.add_field(name='Were you correct? [y/n]', value=wiki_search)
                    prompt_msg.set_author(name=f' for {session.context.author.display_name}',
                                          icon_url=session.context.author.avatar_url)
                    await message.channel.send(embed=prompt_msg)