import traceback

import discord
from discord.ext import commands
from sqlalchemy.sql.expression import func

from answer_validator import validate, Correctness
from database import get_quizdb_session, Bonus, Tournament, TrainingData, get_pkbot_session, PkSession
from driver import SessionState, get_session, Session, end
from settings import get_global_state, parse_arguments
from utils import html_to_discord, get_wikipedia_search, hyperlink, dictionary_to_embed


def session_to_db_object(stats, session):
    return PkSession(discord_user=session[0].author.id, bonuses_heard=str(stats['Bonuses']),
                     points=str(stats['points']), settings=str(session[1]))

class PkSessionState(SessionState):
    def __init__(self):
        self.bonuses = []
        self.bonus_parts_answered = 0
        self.bonuses_answered = 0
        self.points = 0
        self.current_bonus = None
        self.prompting = False



    def stats(self):
        return ({
            'Bonuses': self.bonuses_answered,
            'Points': self.points,
            'PPB': self.points / self.bonuses_answered if self.bonuses_answered > 0 else 'N/A'
        },
        session_to_db_object
        )

def setup(bot):
    cog = PkCog(bot)
    bot.add_cog(cog)



COLLECTING_TRAINING_DATA = True
CORRECTNESS_MAP = {'0': 0, '1': 1, '2': 2, 'y': 0, 'n': 1, 'p': 2}
class PkCog(commands.Cog):
    def get_bonus_batch(self, arguments, batch_size=20):
        if not hasattr(self, 'db_session'):
            # initialize ourselves a session into db
            self.db_session = get_quizdb_session()
        difficulties, categories, subcategories, selected_tournaments = parse_arguments(arguments)

        # Big expression here filters for bonuses that match difficulty, category, subcategory, and tournament
        bonuses = self.db_session.query(Bonus)
        if len(categories) > 0:
            bonuses = bonuses.filter(Bonus.category_id.in_(categories))
        if len(subcategories) > 0:
            bonuses = bonuses.filter(Bonus.subcategory_id.in_(subcategories))
        if len(selected_tournaments) > 0:
            bonuses = bonuses.filter(Bonus.tournament_id.in_(selected_tournaments))
        if len(difficulties) > 0:
            bonuses = bonuses.join(Tournament).filter(Tournament.difficulty.in_(difficulties))
        bonuses = bonuses.order_by(func.random()).limit(batch_size)
        print(str(bonuses)) # print out SQL statement
        output = list()
        for bonus in bonuses:
            output.append((bonus, bonus.bonus_parts, bonus.tournament))

        return output

    @commands.command()
    async def pk(self, ctx, *args):
        state = get_global_state()
        state.skip_message = ctx.message
        if all([ctx.author != session.context.author for session in state.sessions]):
            new_session = Session(ctx, args, PkSessionState())
            state.sessions.append(new_session)
            await self.send_question(ctx.channel, new_session)
        else:
            await ctx.send(f'{ctx.author} is already in a session')

    async def send_question(self, channel, session):
        session_state = session.session_state

        if len(session_state.bonuses) <= 1:
            try:
                session_state.bonuses.extend(self.get_bonus_batch(session.command))
            except Exception as e:
                await channel.send('Error: ' + str(e))
                await channel.send('Stacktrace' + str(traceback.print_tb(e.__traceback__)))
        if session_state.current_bonus is None or session_state.bonus_parts_answered == len(session_state.current_bonus[1]):
            try:
                session_state.current_bonus = session_state.bonuses.pop()
            except IndexError as e:
                await channel.send('Search returned 0 results -- ending pk')
                await end(session.context)
                return

            session_state.bonuses_answered += 1
            leadin_msg = discord.Embed(color=0x00ff00)
            name = session_state.current_bonus[2].name
            if name is None:
                name = 'unknown tournament'
            leadin_msg.add_field(name=f'{name}', value=f'{html_to_discord(session_state.current_bonus[0].leadin)}')
            leadin_msg.set_author(name=f' for {session.context.author.display_name}', icon_url=session.context.author.avatar_url)
            await channel.send(embed=leadin_msg)
            session_state.bonus_parts_answered = 0

        bonus_part = discord.Embed(color=0x0000ff)
        bonus_part.add_field(name=str(session_state.bonus_parts_answered + 1), value=html_to_discord(session_state.current_bonus[1][session_state.bonus_parts_answered].formatted_text))
        bonus_part.set_author(name=f' for {session.context.author.display_name}',
                              icon_url=session.context.author.avatar_url)

        await channel.send(embed=bonus_part)

    @commands.Cog.listener()
    async def on_message(self, message):
        if get_global_state().skip_message is not None and message.id == get_global_state().skip_message.id:
            # skip it, it was used for a bot command
            return
        if message.content.startswith('_'):
            # skip skip
            return

        session = get_session(message.author, PkSessionState)
        if session is not None:
            if session.session_state.prompting:
                session.session_state.prompting = False
                if message.content.lower().startswith('y'):
                    session.session_state.points += 10
                if COLLECTING_TRAINING_DATA:
                    answerline = html_to_discord(session.session_state.current_bonus[1][session.session_state.bonus_parts_answered].formatted_answer)
                    correctness = CORRECTNESS_MAP[message.content.lower()]
                    data = TrainingData(given_answer=self.given_answer, correctness=correctness, formatted_answer=answerline)
                    if not hasattr(self, 'pkbot_session'):
                        # initialize ourselves a session into db
                        self.pkbot_session = get_pkbot_session()
                    self.pkbot_session.add(data)
                    self.pkbot_session.commit()

                message.content.lower()
                session.session_state.bonus_parts_answered += 1
                await self.send_question(message.channel, session)
            else:
                self.given_answer = message.content
                answerline = html_to_discord(session.session_state.current_bonus[1]\
                    [session.session_state.bonus_parts_answered].formatted_answer)
                correctness, formatted_answer, main_answer, unformatted_main_answer, correct_answers = validate(self.given_answer, answerline)
                if COLLECTING_TRAINING_DATA:
                    correctness = Correctness.PROMPT
                if correctness == Correctness.INCORRECT:
                    session.session_state.bonus_parts_answered += 1
                    # break out early - definitely not the answer
                    incorrect_msg = discord.Embed(color=0xff0000)
                    wiki_search = hyperlink(html_to_discord(formatted_answer),
                                            get_wikipedia_search(unformatted_main_answer))
                    incorrect_msg.add_field(name='Sorry, incorrect', value=wiki_search)
                    incorrect_msg.set_author(name=f' for {session.context.author.display_name}',
                                           icon_url=session.context.author.avatar_url)
                    await message.channel.send(embed=incorrect_msg)
                    await self.send_question(message.channel, session)
                    return
                elif correctness == Correctness.CORRECT:
                    session.session_state.points += 10
                    session.session_state.bonus_parts_answered += 1
                    correct_msg = discord.Embed(color=0x0000ff)
                    wiki_search = hyperlink(html_to_discord(formatted_answer), get_wikipedia_search(unformatted_main_answer))
                    correct_msg.add_field(name='Correct', value=wiki_search)
                    correct_msg.set_author(name=f' for {session.context.author.display_name}',
                                          icon_url=session.context.author.avatar_url)
                    await message.channel.send(embed=correct_msg)
                    await self.send_question(message.channel, session)
                else:
                    session.session_state.prompting = True
                    # await message.channel.send(
                    #    f'DEBUG: correct_answers = {correct_answers}, similarities = {[fuzz.ratio(ans.lower(), given_answer.lower()) for ans in correct_answers]}')
                    prompt_msg = discord.Embed(color=0xff0000)
                    wiki_search = hyperlink(html_to_discord(formatted_answer),
                                            get_wikipedia_search(unformatted_main_answer))
                    prompt_msg.add_field(name='Were you correct? [y/n/p]', value=wiki_search)
                    if COLLECTING_TRAINING_DATA:
                        prompt_msg.add_field(name='Bonus part id', value=session.session_state.current_bonus[1]\
                            [session.session_state.bonus_parts_answered].id)
                    prompt_msg.set_author(name=f' for {session.context.author.display_name}',
                                           icon_url=session.context.author.avatar_url)
                    await message.channel.send(embed=prompt_msg)