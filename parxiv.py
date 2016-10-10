#!/usr/local/bin/python
from __future__ import print_function
"""
usage:
    python parxiv.py file.tex

this will make arxiv-somelongdatestring with
    - file_strip.tex (where includegraphics paths are stripped)
    - file_strip.bbl (you should have teh .bbl file already)
    - all figures
"""


def strip_comments(source):
    """
    from https://gist.github.com/amerberg/a273ca1e579ab573b499
    """
    import ply.lex
    tokens = ('PERCENT', 'BEGINCOMMENT', 'ENDCOMMENT', 'BACKSLASH',
              'CHAR', 'BEGINVERBATIM', 'ENDVERBATIM', 'NEWLINE',
              'ESCPCT',
              )
    states = (('linecomment', 'exclusive'),
              ('commentenv', 'exclusive'),
              ('verbatim', 'exclusive')
              )

    # Deal with escaped backslashes, so we don't think they're escaping %.
    def t_BACKSLASH(t):
        r"\\\\"
        return t

    # One-line comments
    def t_PERCENT(t):
        r"\%"
        t.lexer.begin("linecomment")

    # Escaped percent signs
    def t_ESCPCT(t):
        r"\\\%"
        return t

    # Comment environment, as defined by verbatim package
    def t_BEGINCOMMENT(t):
        r"\\begin\s*{\s*comment\s*}"
        t.lexer.begin("commentenv")

    # Verbatim environment (different treatment of comments within)
    def t_BEGINVERBATIM(t):
        r"\\begin\s*{\s*verbatim\s*}"
        t.lexer.begin("verbatim")
        return t

    # Any other character in initial state we leave alone
    def t_CHAR(t):
        r"."
        return t

    def t_NEWLINE(t):
        r"\n"
        return t

    # End comment environment
    def t_commentenv_ENDCOMMENT(t):
        r"\\end\s*{\s*comment\s*}"
        # Anything after \end{comment} on a line is ignored!
        t.lexer.begin('linecomment')

    # Ignore comments of comment environment
    def t_commentenv_CHAR(t):
        r"."
        pass

    def t_commentenv_NEWLINE(t):
        r"\n"
        pass

    # End of verbatim environment
    def t_verbatim_ENDVERBATIM(t):
        r"\\end\s*{\s*verbatim\s*}"
        t.lexer.begin('INITIAL')
        return t

    # Leave contents of verbatim environment alone
    def t_verbatim_CHAR(t):
        r"."
        return t

    def t_verbatim_NEWLINE(t):
        r"\n"
        return t

    # End a % comment when we get to a new line
    def t_linecomment_ENDCOMMENT(t):
        r"\n"
        t.lexer.begin("INITIAL")
        # Newline at the end of a line comment is stripped.

    # Ignore anything after a % on a line
    def t_linecomment_CHAR(t):
        r"."
        pass

    # Error handling rule
    def t_error(t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def t_linecomment_error(t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def t_verbatim_error(t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def t_commentenv_error(t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    lexer = ply.lex.lex()
    lexer.input(source)
    return u"".join([tok.value for tok in lexer])


def find_figs(source):
    """
    look for \graphicspath{{subdir}}  (a single subdir)

    find figures in \includegraphics[something]{PATH/filename.ext}
                    \includegraphics{PATH/filename.ext}

    make them       \includegraphics[something]{filename.ext}
                    \includegraphics{filename.ext}

    copy figures to arxivdir
    """
    import re
    import os

    findgraphicspath = re.search(r'\\graphicspath{(.*)}', source)
    if findgraphicspath:
        graphicspaths = findgraphicspath.group(1)
        graphicspaths = re.findall('{(.*?)}', graphicspaths)
    else:
        graphicspaths = []

    # keep a list of (figname, figpath)
    figlist = []

    def repl(m):

        figpath = ''
        figname = os.path.basename(m.group(2))
        figpath = os.path.dirname(m.group(2))
        newincludegraphics = m.group(1) + figname + m.group(3)

        figlist.append((figname, figpath))
        return newincludegraphics

    source = re.sub(r'(\includegraphics\[.*?\]{)(.*?)(})', repl, source)

    return figlist, source, graphicspaths


def flatten(source):
    """
    replace arguments of include{} and intput{}
    assumes no comments
    """
    import re
    import io

    def repl(m):
        with io.open(m.group(2), encoding='utf-8') as f:
            newtext = f.read()
        return newtext
    dest = re.sub(r'(\\input{)(.*?)(})', repl, source)
    return dest


def main(fname):
    import io
    import time
    import os
    import shutil
    import glob

    print('[parxiv] reading %s' % fname)
    with io.open(fname, encoding='utf-8') as f:
        source = f.read()

    print('[parxiv] stripping comments')
    source = strip_comments(source)
    print('[parxiv] flattening source')
    source = flatten(source)
    print('[parxiv] stripping comments again')
    source = strip_comments(source)
    print('[parxiv] finding figures...')
    figlist, source, graphicspaths = find_figs(source)

    print('[parxiv] making directory', end='')
    dirname = 'arxiv-' + time.strftime('%c').replace(' ', '-')
    dirname = dirname.replace(':', '-')
    print(' %s' % dirname)
    os.makedirs(dirname)

    print('[parxiv] copying figures', end='')
    print('             ... ', end='')
    for figname, figpath in figlist:

        _, ext = os.path.splitext(figname)
        if ext is '':
            figname += '.pdf'

        allpaths = graphicspaths
        if(len(figpath) > 0):
            allpaths = [figpath] + allpaths
        allpaths += './'

        for p in allpaths:
            src = os.path.join(p, figname)
            dest = os.path.join(dirname, os.path.basename(figname))
            try:
                shutil.copy2(src, dest)
            except IOError
            # then try graphicspath in order
        except:
            base = os.path.join(dirname, os.path.basename(fig))
            for newfig in glob.glob(base+'.*'):
                shutil.copy2(fig, os.path.join(dirname, os.path.basename(fig)))

    bblfile = fname.replace('.tex', '.bbl')
    newbblfile = fname.replace('.tex', '_strip.bbl')
    shutil.copy2(bblfile, os.path.join(dirname, newbblfile))

    with io.open(
            os.path.join(dirname, fname.replace('.tex', '_strip.tex')),
            'w') as fout:
        fout.write(source)

    return source

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('usage: python parxiv.py <filename.tex>')
        sys.exit(-1)

    fname = sys.argv[1]
    source = main(fname)
