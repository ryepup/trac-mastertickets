# Created by Ryan Davis and Russ Tyndall on 2010-09-30.
# Copyright (c) 2010 Ryan Davis. All rights reserved.
import time
from trac.web.href import Href
from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.db import DatabaseManager
from trac.wiki.api import IWikiMacroProvider, parse_args
from trac.wiki.formatter import Formatter
from trac.ticket.model import Ticket
from model import *
from StringIO import StringIO
from genshi.core import Markup

class Options:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    

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
                'fontsize':"12",
                'show_ticket_number':"1",
                'milestone':'',
                'group_by_milestone':'1',
                'debug':'0',
                'word_wrap_char_limit':'30'}


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
        def escape(txt, chars):
            if chars:
                char = chars.pop()
                return escape(txt.replace(char, '\\'+char), chars)
            else:
                return txt

        # from http://code.activestate.com/recipes/148061-one-liner-word-wrap-function/
        def wrap(text, width):
            """
            A word-wrap function that preserves existing line breaks
            and most spaces in the text. Expects that existing line
            breaks are posix newlines (\n).
            """
            return reduce(lambda line, word, width=width: '%s%s%s' %
                          (line,
                           ' \n'[(len(line)-line.rfind('\n')-1
                                  + len(word.split('\n',1)[0]
                                        ) >= width)],
                           word),
                          text.split(' ')
                          )

        # http://www.colourlovers.com/palette/1930/cheer_up_emo_kid
        opts = MasterTicketsMacros.DEFAULT_OPTIONS.copy()
        opts['label'] =  "as of %s" % time.asctime()
        opts['graph_name'] = str(int(time.time()))
        
        if args == None and content:
            x,args = parse_args(content)
            

        if args:
            opts.update(args)        



        # convert boolean options to actual booleans
        for bopt in ['show_ticket_number','group_by_milestone', 'debug']:
            opts[bopt] = opts[bopt] == '1'

        for iopt in ['word_wrap_char_limit', 'fontsize']:
            opts[iopt] = int(opts[iopt])

        word_wrap_char_limit = Options(**opts).word_wrap_char_limit
        def q(txt):
            return '"%s"' % escape(wrap(txt, word_wrap_char_limit), list('"')).replace('\n', '\\n')


        # quote things we should quote
        for o in ['unblocked_color','unblocked_linkcolor', 'blocked_color', 'blocked_linkcolor', 'closed_color', 'closed_linkcolor', 'critical_color', 'critical_linkcolor', 'label', 'graph_name']:
            opts[o] = q(opts[o])

        
        opts = Options(**opts)




        opts.milestone = [x.lower() for x in opts.milestone.split('|') if len(x)>0]

        def has_good_milestone(tkt):
            if opts.milestone:
                return tkt['milestone'] and tkt['milestone'].lower() in opts.milestone
            else:
                return True

        tickets = {}
        def ensure_ticket(tktid):
            if not tickets.has_key(tktid):
                tkt = Ticket(self.env, tktid)
                if has_good_milestone(tkt):
                    tickets[tktid] = tkt
                    tickets[tktid]['mastertickets_blocking'] = set()
            return tickets.get(tktid)

        default_nodeopts = {'color': opts.blocked_color,
                            'fontcolor':opts.blocked_linkcolor,
                            'fontsize':opts.fontsize,
                            'margin':'.15,.15'}

        unblocked_attributes = {'color': opts.unblocked_color,
                                'fontcolor':opts.unblocked_linkcolor,
                                'style': "filled"}
            
        critical_attributes = {'color': opts.critical_color,
                               'fontcolor':opts.critical_linkcolor,
                               'style': "filled"}

        closed_attributes = {'color': opts.closed_color,
                             'fontcolor':opts.closed_linkcolor,
                             'style': "filled"}

        def write_node(writer, node_name, **attrs):
            writer.write("%s [" % node_name)            
            for k,v in attrs.items():
                writer.write('%s=%s,' % (k, v))
            writer.write("]\n")
            

        #parse args from content
        final = "error"
        try:
            dot = StringIO()
            dot.write("""digraph %s{
  label=%s
""" % (opts.graph_name, opts.label))
            
            write_node(dot, 'node', **default_nodeopts)

            dot.write("""subgraph cluster0{
  label="Legend"
""")

            write_node(dot, 'closed', label=q('Closed / Done'), **closed_attributes)
            write_node(dot, 'unblocked', label=q('Unblocked / Ready'), **unblocked_attributes)
            write_node(dot, 'critical', label=q('Active'), **critical_attributes)
            write_node(dot, 'blocked', label=q('Blocked'))

            dot.write("}")


            blocked_ids = set()

            #render the edges and build up some hashes we'll need for node rendering
            for (src, dst) in all_links(self.env):
                src_tkt = ensure_ticket(src)
                dst_tkt = ensure_ticket(dst)

                if src_tkt == None:
                    continue
                if dst_tkt != None:
                    src_tkt['mastertickets_blocking'].add(dst)
                    if src_tkt['status'] != 'closed':
                        blocked_ids.add(dst)

            edges = StringIO()
            #render the nodes
            h = Href(formatter.req.base_url)

            

            def write_ticket_node(writer, tktid, tkt):
                nodeopts = default_nodeopts.copy()
                nodeopts['URL'] = q(h.ticket(tktid))

                nodeopts['label'] = q(tkt['summary'])

                if opts.show_ticket_number:
                    nodeopts['shape'] = 'record'
                    nodeopts['label'] = q('%s|%s' % (tktid, escape(tkt['summary'], list('|<>{}'))))


                
                # color differently if we're not blocked
                if tktid not in blocked_ids:
                    nodeopts.update(unblocked_attributes)

                if tkt['priority'] == 'critical':
                    nodeopts.update(critical_attributes)

                # color differently if we're closed
                if tkt['status'] == 'closed':
                    nodeopts.update(closed_attributes)

                writer.write("ticket%s [" % tktid)
                for k,v in nodeopts.items():
                    writer.write('%s=%s,' % (k, v))
                writer.write("]\n")

                for dst in tkt['mastertickets_blocking']:
                    edges.write("ticket%s -> ticket%s" % (tktid, dst))
                    if tkt['status'] == 'closed':
                        edges.write(" [style=dashed,color=%s]" % (opts.closed_color))
                    edges.write('\n')

            milestones = {}

            def milestone_writer(milestone):
                if not milestones.has_key(milestone):
                    milestones[milestone] = StringIO()
                return milestones[milestone]

            for (tktid, tkt) in tickets.items():
                writer = opts.group_by_milestone and milestone_writer(tkt['milestone']) or dot
                write_ticket_node(writer, tktid, tkt)

            

            cluster = 1
            for milestone,io in milestones.items():
                if milestone == '':
                    dot.write(io.getvalue())
                else:
                    dot.write("""
subgraph cluster%s{
  label=%s
%s
}
""" % (cluster, q(milestone), io.getvalue()))
                    cluster += 1

            dot.write(edges.getvalue())
            dot.write("}")

            out = StringIO()
            graphviz = StringIO()
            graphviz.write("""{{{#!graphviz
%s
}}}""" % (dot.getvalue()))
            if opts.debug:
                graphviz.write("""
{{{
%s
}}}""" % (dot.getvalue()))

            Formatter(formatter.env, formatter.context).format(graphviz.getvalue(), out)
            final = Markup(out.getvalue())
        except Exception, e:
            self.log.exception('RPD%s', e)
            TracError(e)
            final = '%s' % (e)
        return final
   
 
