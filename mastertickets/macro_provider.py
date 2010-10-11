# Created by Ryan Davis and Russ Tyndall on 2010-09-30.
# Copyright (c) 2010 Ryan Davis. All rights reserved.
import time

from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.db import DatabaseManager
from trac.wiki.api import IWikiMacroProvider
from trac.wiki.formatter import Formatter
from trac.ticket.model import Ticket
from model import *
from StringIO import StringIO
from genshi.core import Markup

class MasterTicketsMacros(Component):
    """Central functionality for the MasterTickets plugin."""

    implements(IWikiMacroProvider)

    DEFAULT_OPTIONS = {'unblocked_color':"#4ECDC4",
                'unblocked_linkcolor':"blue",
                'blocked_color':"black",
                'blocked_linkcolor':"blue",
                'closed_color':"#556270",
                'closed_linkcolor':"#4ECDC4",
                'critical_color':"#C7F464",
                'critical_linkcolor':"blue",
                'fontsize':"12"}


    def get_macros(self):
        """Return an iterable that provides the names of the provided macros.
        """
        return ["DepGraph"]

    def get_macro_description(self,name):
        """Return a plain text description of the macro with the specified
        name."""
        keys = MasterTicketsMacros.DEFAULT_OPTIONS.keys()
        keys.sort()
        desc ={'DepGraph': "shows the dependency graph for all tickets, can customize a few colors:\n%s" % 
               '\n'.join([" * {{{%s}}}: {{{%s}}}" % (k, MasterTicketsMacros.DEFAULT_OPTIONS[k]) for k in keys])}
        return desc[name]

    def expand_macro(self,formatter, name, content, args=None):
        """Called by the formatter when rendering the parsed wiki text.

        This form is preferred over `render_macro`, as you get the
        formatter, which knows the current `.context` (and the `.req`,
        but ideally you shouldn't use it in your macros). (''since 0.11'')

        `name` is the name by which the macro has been called; remember
        that via `get_macros`, multiple names could be associated to this
        macros. Note that the macro names are case sensitive.
        
        `content` is the content of the macro call. When called using macro
        syntax (`[[Macro(content)]]`), this is the string contained between
        parentheses, usually containing macro arguments. When called using wiki
        processor syntax (`{{{!#Macro ...}}}`), it is the content of the
        processor block, that is, the text starting on the line following the
        macro name.

        `args` will be a dictionary containing the named parameters which you
        can specify when calling the macro using the wiki processor syntax:
        `{{{#!Macro arg1=value1 arg2="value 2"`. In this example, `args` will
        be `{'arg1': 'value1', 'arg2': 'value 2'}`).
        If no named parameters are given, `args` will be `{}`. That makes it
        possible to differentiate with a call using the macro syntax, in which
        case `args` will be `None` (see `parse_args` for a convenient way to
        extract arguments and name parameters from the `content` inside the
        parentheses, in the latter situation). (''since 0.12'')
        """
        def q(txt):
            return '"%s"' % txt.replace('"', '\\"')

        # http://www.colourlovers.com/palette/1930/cheer_up_emo_kid
        opts = MasterTicketsMacros.DEFAULT_OPTIONS.copy()
        opts['label'] =  "as of %s" % time.asctime()
        opts['graph_name'] = str(int(time.time()))

        if args:
            opts.update(args)

        #parse args from content
        final = "error"
        try:
            dot = StringIO()
            dot.write("""{{{
#!graphviz
digraph %s{
  label=%s
""" % (q(opts['graph_name']), q(opts['label'])))
            tickets = {}
            def ensure_ticket(tkt):
                if not tickets.has_key(tkt):
                    tickets[tkt] = Ticket(self.env, tkt)
                return tickets[tkt]

            blocked = {}

            #render the edges and build up some hashes we'll need for node rendering
            for (src, dst) in all_links(self.env):
                dot.write("ticket%s -> ticket%s\n" % (src, dst))
                tkt = ensure_ticket(src)
                ensure_ticket(dst)
                if tkt['status'] != 'closed':
                    blocked[dst] = True
            
            blocked_ids = blocked.keys()
            

            #render the nodes
            for (tktid, tkt) in tickets.items():
                #default options
                nodeopts = {'label':q(tkt['summary']),
                            'color': q(opts['blocked_color']),
                            'fontcolor':q(opts['blocked_linkcolor']),
                            'fontsize':q(opts['fontsize']),
                            'URL':q(self.env.href.ticket(tktid))}
                
                # color differently if we're not blocked
                if tktid not in blocked_ids:
                    nodeopts['color'] = q(opts['unblocked_color'])
                    nodeopts['fontcolor'] = q(opts['unblocked_linkcolor'])
                    nodeopts['style'] = "filled"

                if tkt['priority'] == 'critical':
                    nodeopts['color'] = q(opts['critical_color'])
                    nodeopts['fontcolor'] = q(opts['critical_linkcolor'])
                    nodeopts['style'] = "filled"

                # color differently if we're closed
                if tkt['status'] == 'closed':
                    nodeopts['color'] = q(opts['closed_color'])
                    nodeopts['fontcolor'] = q(opts['closed_linkcolor'])
                    nodeopts['style'] = "filled"

                dot.write("ticket%s [" % tktid)
                for k,v in nodeopts.items():
                    dot.write('%s=%s,' % (k, v))
                dot.write("]\n")

            dot.write("""subgraph cluster0{
  label="Legend"
""")
            dot.write("closed[label=\"Closed / Done\",color=%s,fontcolor=%s,fontsize=%s,style=filled]\n" %
                      (q(opts['closed_color']),q(opts['closed_linkcolor']),q(opts['fontsize']),))
            dot.write("unblocked[label=\"Unblocked / Ready\",color=%s,fontcolor=%s,fontsize=%s,style=filled]\n" %
                      (q(opts['unblocked_color']),q(opts['unblocked_linkcolor']),q(opts['fontsize']),))
            dot.write("critical[label=\"Active\",color=%s,fontcolor=%s,fontsize=%s,style=filled]\n" %
                      (q(opts['critical_color']),q(opts['critical_linkcolor']),q(opts['fontsize']),))
            dot.write("blocked[label=\"Blocked / Waiting\",color=%s,fontcolor=%s,fontsize=%s]\n" %
                      (q(opts['blocked_color']),q(opts['blocked_linkcolor']),q(opts['fontsize']),))

            dot.write("}")

            dot.write("""}
}}}""")

            out = StringIO()
            Formatter(formatter.env, formatter.context).format(dot.getvalue(), out)
            final = Markup(out.getvalue())
        except Exception, e:
            self.log.exception('RPD%s', e)
            TracError(e)

        return final
   
 
