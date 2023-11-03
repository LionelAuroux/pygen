from pygen import *
import logging

log = logging.getLogger(__name__)

def test_lines():
    log.info("LINES")
    pcg = Codegen()
    l = Line("     something", pcg)
    assert not l.is_data_begin
    assert not l.is_data_end
    assert not l.is_protect_begin
    assert not l.is_protect_end
    assert not l.is_script_begin
    assert not l.is_script_end
    assert not l.is_markup
    l = Line("     /*##begin_data##*/", pcg)
    assert l.is_data_begin
    l = Line("     /*##end_data##*/", pcg)
    assert l.is_data_end
    l = Line("     /*##begin_protect##*/", pcg)
    assert l.is_protect_begin
    l = Line("     /*##end_protect##*/", pcg)
    assert l.is_protect_end
    l = Line("     /*##script##", pcg)
    assert l.is_script_begin
    l = Line("     ##script##*/", pcg)
    assert l.is_script_end
    l = Line('     /*##markup##*/', pcg)
    assert not l.is_markup
    assert l.markup_key is None
    l = Line('     /*##markup##"this is a test"*/', pcg)
    assert l.is_markup
    assert l.markup_key == "this is a test"
    assert l.deindent() == '/*##markup##"this is a test"*/'
    assert l.deindent(2) == '   /*##markup##"this is a test"*/'
    assert l.deindent(3) == '  /*##markup##"this is a test"*/'
    assert l.deindent(5) == '/*##markup##"this is a test"*/'
    assert l.deindent(10) == '/*##markup##"this is a test"*/'

def test_basic():
    log.info("CODE GEN")
    cg = Codegen()
    data = """\
    ceci est un test
    """
    cg.setContent(data)
    o = cg.processContent()
    assert data == o, "Failed to processContent"
    data = """\
    ceci est un test
    /*##markup##"markup key"*/
    """
    cg.setContent(data)
    o = cg.processContent()
    log.info(f"DATA <{o}>")
    assert data == o, "Failed to processContent"
    data = """\
    ceci est un test
    /*##script##
        pygen.log.info('EXECUTE LE SCRIPT')
        a = 12
    */
    """
    cg.setContent(data)
    o = cg.processContent()
    log.info(f"DATA <{o}>")
    assert data == o, "Failed to processContent"
    assert 'a' in cg.pygen.locals
    assert cg.pygen.locals['a'] == 12
    data = """\
    ceci est un test
    /*##script##
        pygen.log.info('EXECUTE LE SCRIPT')
        a = 12
    */
    DO SOMETHING ELSE
    /*##script##
        pygen.log.info(f'EXECUTE LE SCRIPT with {a}')
        b = a + 4
    */
    """
    cg.setContent(data)
    o = cg.processContent()
    log.info(f"DATA <{o}>")
    assert data == o, "Failed to processContent"
    assert 'a' in cg.pygen.locals
    assert 'b' in cg.pygen.locals
    assert cg.pygen.locals['a'] == 12
    assert cg.pygen.locals['b'] == 16
    data = """\
    ceci est un test
    /*##script##
        pygen.log.info('EXECUTE LE SCRIPT')
        if 'markup key' in pygen.markups:
            pygen.log.info('FOUND Markup')
            pygen.markups['markup key'].addData('''\
                Coucou
                C'est la vie''')
    */
    /*##markup##"markup key"*/
    """
    cg.setContent(data)
    o = cg.processContent()
    log.info(f"DATA <{o}>")
    assert o == data + """\n/*##begin_data##*/
            Coucou
            C'est la vie
/*##end_data##*/
    """, "Failed to processContent"

def test_deindent():
    log.info("UTILS FUN")
    # cas standard
    t = deindent("   blop")
    assert t == "blop"
    # enleve exactement le bon nombre d'espace
    t = deindent("""\
        blop
        blip
        if blup:
            blap
        """)
    assert t == """blop\nblip\nif blup:\n    blap\n"""
    # enleve a minima le bon nombre d'espace
    t = deindent("""\
        blop
        blip
        if blup:
            blap
    """)
    assert t == """blop\nblip\nif blup:\n    blap\n"""
    # enleve un prefix
    t = deindent("""\
        -- blop
        -- blip
        -- if blup:
        --     blap
    """, prefix="-- ")
    assert t == """blop\nblip\nif blup:\n    blap\n"""
