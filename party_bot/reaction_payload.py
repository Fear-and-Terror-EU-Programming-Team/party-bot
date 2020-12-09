import config


class ReactionPayload:
    """
    Object containing context information for an emoji reaction, such as
    the channel, the member that made the reaction, and the emoji itself.

    This is used to convert the payload object supplied to on_raw_reaction_add
    etc. into a more usable form containing Discord objects instead of IDs.

    Do not create a ReactionPayload object manually.
    Instead, use the `unwrap_payload` function.
    """

    # this might be a bit heavy on the API
    async def _init(self, payload):
        self.guild = config.bot.get_guild(payload.guild_id)
        self.member = await self.guild.fetch_member(payload.user_id)
        self.emoji = payload.emoji
        self.channel = config.bot.get_channel(payload.channel_id)
        self.message = await self.channel.fetch_message(payload.message_id)


async def unwrap_payload(payload):
    """
    Converts a payload object supplied to `on_raw_reaction_add` etc. into a
    more useful `ReactionPayload` object containing Discord objects instead of
    IDs.
    """
    rp = ReactionPayload()
    await rp._init(payload)
    return rp
