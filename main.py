import discord
import time
import stripe
from config import *
from datetime import date, datetime, timedelta
from discord.ui import Button, View
from discord.ext import commands
from discord.utils import get
from math import perm
from string import digits

# Create today event for general embed information
today = date.today()
current_time = datetime.utcnow()

# Enable Stripe system (if enabled)
if Config.stripe['enabled']:
    stripe.api_key = Config.stripe['key']

# Create bot event
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create class for starting bot to allow for persistent views
class StartBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(Config.prefix), intents=intents)
        self.persistent_views_added = False
    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(PersistentVerification())
            self.add_view(DonationView())
            self.persistent_views_added = True
        print(f"We have logged in as {bot.user}")
        if Config.bot_status['enabled']:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=Config.bot_status['message']), status=Config.bot_status['status'])

class PersistentVerification(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(custom_id='persistent_view:verification', label='Verify', style=discord.ButtonStyle.gray)
    async def verification(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild = bot.get_guild(Config.guild)
        unverified = guild.get_role(Config.verification_system['unverifiedRole'])
        verified = guild.get_role(Config.verification_system['verifiedRole'])
        member = guild.get_member(interaction.user.id)

        if verified is None or unverified is None:
            return
        else:
            await member.remove_roles(unverified)
            await member.add_roles(verified)
            await interaction.response.send_message("You have verified yourself. Welcome to the server!", ephemeral=True)

if Config.stripe['enabled']:
    class DonationDropdown(discord.ui.Select):
        def __init__(self):

            options = [
                discord.SelectOption(label="5", description="$5"),
                discord.SelectOption(label="10", description="$10"),
                discord.SelectOption(label="15", description="$15"),
                discord.SelectOption(label="20", description="$20"),
                discord.SelectOption(label="25", description="$25"),
            ]

            super().__init__(
                custom_id="persistent_view:donation",
                placeholder="Select Your Donation Amount",
                min_values=1,
                max_values=1,
                options=options,
            )

        async def callback(self, interaction: discord.Interaction):
            amount = int(self.values[0])
            customer = stripe.Customer.create(name=interaction.user.display_name, description = f"{interaction.user.display_name}#{interaction.user.discriminator}")
            product = stripe.InvoiceItem.create(currency = 'usd', customer = customer.id, amount = (amount * 100))
            invoice = stripe.Invoice.create(customer = customer.id)
            stripe.Invoice.finalize_invoice(invoice.id)
            redirect = stripe.Invoice.retrieve(invoice.id)

            embed = await embed_builder("Donation Page Created", f"Your donation has been setup. Please click the button below to complete your donation for the amount of ${amount}.")
            view = await createLinkButton("Finalize Donation", f"{redirect.hosted_invoice_url}")
            await interaction.user.send(embed=embed, view=view)
            await interaction.response.send_message(f"Check your DMs to complete your donation of ${self.values[0]}", ephemeral=True)

    class DonationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

            # Adds the dropdown to our view object.
            self.add_item(DonationDropdown())

bot = StartBot()

@bot.event
async def on_member_join(member):
    # If welcome_channel module is enabled
    if Config.welcome_channel['enabled']:
        date = member.created_at
        embed = await embed_builder("Welcome User!", f"<@{member.id}> ({member.display_name}#{member.discriminator}) has joined the server.\n\n**Account Age**:\n{date.strftime('%x')}, {date.strftime('%X')}", thumbnail = True, footer = True)
        welcome_channel = bot.get_channel(Config.welcome_channel['channelID'])

        await welcome_channel.send(embed=embed)

        # If welcome_channel module doesn't have a default role and the verification_system module is enable
        if not Config.welcome_channel['defaultRole'] and Config.verification_system['enabled'] == True:
            # Add unverifiedRole
            role = discord.utils.get(bot.get_guild(member.guild.id).roles, id=Config.verification_system['unverifiedRole'])
            await member.add_roles(role)

            # Send private message to user to verify themselves
            embed = await embed_builder("Verify Yourself", f"To get access to the server, you need to verify yourself. Please click the button below to continue.", thumbnail = True, footer = True)
            await member.send(embed=embed, view=PersistentVerification())
        # If welcome_channel module does have a default role or the verification_system module is disabled
        else:
            role = discord.utils.get(bot.get_guild(member.guild.id).roles, id=Config.welcome_channel['defaultRole'])
            await member.add_roles(role)

@bot.event
async def on_message(message):
    if len(message.content) > 0:
        if str(message.content[0]) != str(Config.prefix):
            bad_word = any(word.lower() in message.content.lower() for word in Config.filtered)
            if bad_word and not message.author.get_role(Config.admin_role):
                await message.delete()
        else:
            await bot.process_commands(message)

@bot.command(name="embed", alias="sayem")
async def embed(ctx, *, embed = ""):
    if ctx.author.get_role(Config.admin_role):
        await ctx.message.delete()
        if not embed:
            await show_temporary_message(ctx, "Empty Embed", "No embed was provided. Please try again.")
        else:
            embed = await embed_builder("", embed, member = ctx.author)
            await ctx.send(embed=embed)
    else:
        await permission_denied(ctx)

@bot.command(name="timeout", alias="mute")
async def timeout(ctx, member: discord.Member, time = "", *, reason = ""):
    if ctx.author.get_role(Config.admin_role):
        await ctx.message.delete()

        if not time:
            await show_temporary_message(ctx, "No Time", "No time was set for the timeout. Please try again.")
        else:
            length = ''.join(i for i in time if not i.isdigit())
            time_int = [int(word) for word in list(time) if word.isdigit()]
            match length.lower():
                case 'm':
                    duration = current_time + timedelta(minutes=time_int[0])
                case 'h':
                    duration = current_time + timedelta(hours=time_int[0])
                case _:
                    duration = current_time + timedelta(minutes=time_int[0])
            
            await member.timeout(duration, reason=reason)
            await show_temporary_message(ctx, "User Timed out", f"{member.mention} was timed out.")
    else:
        await permission_denied(ctx)

@bot.command(name="kick", alias="remove")
async def kick(ctx, member: discord.Member, *, reason = ""):
    if ctx.author.get_role(Config.admin_role):
        await ctx.message.delete()
        await member.kick(reason=reason)
        await show_temporary_message(ctx, "User Kicked", f"{member.mention} was kicked.")
    else:
        await permission_denied(ctx)

@bot.command(name="ban", alias="perm")
async def ban(ctx, member: discord.Member, *, reason = ""):
    if ctx.author.get_role(Config.admin_role):
        await ctx.message.delete()
        await member.ban(reason=reason)
        await show_temporary_message(ctx, "User Banned", f"{member.mention} was banned.")
    else:
        await permission_denied(ctx)

@bot.command(name="purge", alias="clear")
async def clear(ctx, amount: int):
    if ctx.author.get_role(Config.admin_role):
        await ctx.message.delete()
        await ctx.channel.purge(limit=amount)

        await show_temporary_message(ctx, "Channel Cleared", f"The last **{amount}** messages in this channel have been removed.")
    else:
        await permission_denied(ctx)

if Config.stripe['enabled']:
    @bot.command()
    async def createDonation(ctx, channel: discord.TextChannel, *, body = ""):
        if ctx.author.get_role(Config.admin_role):
            await ctx.message.delete()
            if not body:
                await show_temporary_message(ctx, "No Body Provided", "No body was provided for the creation of the embed. Please try again.")
            else:
                embed = await embed_builder(f"{Config.name} Donations", body)
                await channel.send(embed=embed, view=DonationView())
        else:
            await permission_denied(ctx)

# Function to show permission denied
async def permission_denied(ctx):
    await ctx.message.delete()

    embed = await embed_builder("Permission Denied", "You're not allowed to perform this action.")
    message = await ctx.send(embed=embed)
    time.sleep(5)
    await message.delete()

# Function to show temporary message
async def show_temporary_message(ctx, title, content):
    embed = await embed_builder(title, content, footer = False)
    message = await ctx.send(embed=embed)
    time.sleep(10)
    await message.delete()

# Function for building embeds
async def embed_builder(title, description, member = "", thumbnail = False, footer = True):
    embed = discord.Embed(title=title, description=description, color=discord.Color.from_rgb(18,95,217))
    if footer:
        embed.set_footer(text=f"© {Config.name} {today.strftime('%Y')} • {today.strftime('%m/%d/%Y')}")
    if member:
        embed.set_author(name=f"{member.display_name}#{member.discriminator}", icon_url=member.avatar.url)
    if thumbnail:
        embed.set_thumbnail(url=f"{Config.logo}")

    return embed

# Function for asking questions (might be removed in future versions)
async def askQuestion(ctx, channel, question):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    embed = await embed_builder("", question, False, False)
    msg = await channel.send(embed=embed)
    response = await bot.wait_for(event = 'message', check = check, timeout = 60.0)
    await response.delete()
    await msg.delete()

    return response

# Function to create a View with a link button
async def createLinkButton(label, url):
    view = View()
    button = Button(label=label, style=discord.ButtonStyle.link, url=url)
    view.add_item(button)
    return view

bot.run(Config.token)