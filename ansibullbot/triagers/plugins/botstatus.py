import six

from ansibullbot.utils.extractors import remove_markdown_blockquotes


def get_bot_status_facts(issuewrapper, module_indexer, core_team=[], bot_names=[]):
    """
    Whether a bot_status command needs to be processed
    """
    iw = issuewrapper
    bs = False

    # Traverse the entire history to find out if there's an unfulfilled bot_status
    for ev in iw.history.history:
        if ev[u'event'] != u'commented':
            continue

        body = remove_markdown_blockquotes(ev[u'body'])

        # Toggle bot_status off or on
        if bs:
            # Post by the bot
            if ev[u'actor'] in bot_names:
                # Post is a bot_status comment
                if is_bot_status_comment(body):
                    # The request has already been fulfilled
                    bs = False
                    continue
        else:
            # Make sure the comment is not from the bot or a previous bot_status fulfillment
            if ev[u'actor'] in bot_names or is_bot_status_comment(body):
                continue

            # Only certain people can request bot_status to prevent DOS attacks
            if ev[u'actor'] not in core_team or \
                    ev[u'actor'] != iw.submitter or \
                    ev[u'actor'] not in module_indexer.all_maintainers:
                continue

            # Check for a bot_status command
            if u'bot_status' in body:
                bs = True
                continue

    return {u'needs_bot_status': bs}


def is_bot_status_comment(body):
    """
    Whether the comment being checked was written by a bot_status command

    :arg body: The comment body to check.
    :returns: True if the body looks like a bot_status comment.  Otherwise False.
    """
    body = body.split('\n')

    bot_status = False
    if body[-1] == '<!--- boilerplate: bot_status --->':
            bot_status = True

    return bot_status
