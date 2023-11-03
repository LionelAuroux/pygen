import re
import logging

log = logging.getLogger(__name__)

class ContentParts:
    def __init__(self, lineContent, begin, end):
        self._content = lineContent
        self._begin = begin
        self._end = end

    def process(self, outContent, pygen=None):
        for p in self._content[self._begin:self._end+1]:
            log.info(f"Content ADD P: {len(p)} bytes")
            outContent.append(p)

    def __repr__(self):
        return f"{type(self).__name__}({self._begin}, {self._end})"

class MarkupParts:
    def __init__(self, lineContent, begin, end, name):
        self._content = lineContent
        self._name = name
        self._begin = begin
        self._end = end
        self.__data = []

    def process(self, outContent, pygen=None):
        # rajoute le contenu de markup
        for p in self._content[self._begin:self._end+1]:
            # FIXME: mode auto-effacage, ne se recopie pas et disparait en terme de balisage
            log.info(f"Markup ADD P: {len(p)} bytes")
            # TODO: Ajoute les datas
            outContent.append(p)
            if len(self.__data):
                outContent.append('/*##begin_data##*/')
                for d in self.__data:
                    outContent.append(d)
                outContent.append('/*##end_data##*/')

    def addData(self, sContent, protected_data={}):
        self.__data.append(sContent)

    def __repr__(self):
        return f"{type(self).__name__}({self._begin}, {self._end})"

class DataParts:
    def __init__(self, begin, end):
        self._begin = begin
        self._end = end

class ProtectedParts:
    def __init__(self, begin, end):
        self._begin = begin
        self._end = end

def deindent(sContent, prefix=None):
    # FIXME: gérer les lignes préfixées par beginComment
    log.info("DEINDENT")
    lines = sContent.split('\n')
    # compte le nombre d'espace en début de première ligne
    ws = re.compile(r'^\s*')
    space = ws.match(lines[0])
    if space is not None:
        cntws = str(len(space.group(0)))
        log.info(f"space {space} : <{space.group(0)}>")
        for idx, l in enumerate(lines):
            # enleve a minima les cntws espaces devant
            l = re.sub(r'^\s{,' + cntws + '}', '', l)
            # enleve le prefix
            if prefix is not None:
                l = re.sub(r'^' + prefix, '', l)
            lines[idx] = l
    return '\n'.join(lines)

class ProxyClass:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class ScriptParts:
    def __init__(self, lineContent, begin, end):
        self._content = lineContent
        self._begin = begin
        self._end = end

    def process(self, outContent, pygen):
        # FIXME: mode auto-effacage, ne se recopie pas et disparait en terme de balisage
        for p in self._content[self._begin:self._end+1]:
            log.info(f"Script ADD P: {len(p)} bytes")
            outContent.append(p)
        # TODO: Execute le script avec le ctx
        scriptContent = "\n".join(self._content[self._begin+1:self._end])
        # FIXME: deindent scriptContent
        log.info(f"SCRIPT CONTTENT:\n{scriptContent}")
        code = compile(deindent(scriptContent), "<string_from_>", 'exec')
        g = {}
        g.update(pygen.globals)
        g['pygen'] = pygen
        l = pygen.locals
        #if 'locals' in vars(pygen):
        #    l = pygen.locals
        exec(code, g, l)
        log.info(f"LOCALS : {l}")
        pygen.locals.update(l)

    def __repr__(self):
        return f"{type(self).__name__}({self._begin}, {self._end})"

class Line:
    def __init__(self, line, pygenctx):
        self._pygenctx = pygenctx
        self._line = line
        # compte le nombre d'espace devant
        ws = re.compile(r'^\s*')
        space = ws.match(self._line)
        self._nbspaces = 0
        # mis a jour pas is_markup
        self._markup_key = None
        if space is not None:
            self._nbspaces = len(space.group(0))

    def __getitem__(self, index):
        return self._line[index]

    def deindent(self, nbspaces=None, inplace=False):
        if nbspaces is None:
            nbspaces = self.nbspaces
        l = re.sub(r'^\s{,' + str(nbspaces) + '}', '', self._line)
        if inplace:
            self._line = l
        return l

    @property
    def nbspaces(self):
        return self._nbspaces

    @property
    def markup_key(self):
        return self._markup_key

    @property
    def is_classical(self):
        return not self.is_markup and not self.is_script_begin and not self.data_begin

    @property
    def is_markup(self):
        if self._line.find(self._pygenctx.beginComment + self._pygenctx.markupEntry) != -1:
            mk = re.compile(r'.*##markup##"(?P<markup_key>(?:\\.|[^"\\])+)"')
            # fixme: check le reste avant la fin du markup
            m = mk.match(self._line)
            if m is None:
                return False
            g = m.groupdict()
            self._markup_key = g["markup_key"]
            return True
        return False

    @property
    def is_script_begin(self):
        return self._line.find(self._pygenctx.beginComment + self._pygenctx.scriptEntry) != -1

    @property
    def is_script_end(self):
        return self._line.find(self._pygenctx.scriptEntry + self._pygenctx.endComment) != -1

    @property
    def is_data_begin(self):
        return self._line.find(self._pygenctx.beginComment + self._pygenctx.dataBegin + self._pygenctx.endComment) != -1

    @property
    def is_data_end(self):
        return self._line.find(self._pygenctx.beginComment + self._pygenctx.dataEnd + self._pygenctx.endComment) != -1

    @property
    def is_protect_begin(self):
        return self._line.find(self._pygenctx.beginComment + self._pygenctx.protectBegin + self._pygenctx.endComment) != -1

    @property
    def is_protect_end(self):
        return self._line.find(self._pygenctx.beginComment + self._pygenctx.protectEnd + self._pygenctx.endComment) != -1

class Codegen:
    def __init__(self, eol='\n'
            , begin_comment="/*"
            , end_comment="*/"
            , markup_entry="##markup##"
            , script_entry="##script##"
            , data_begin="##begin_data##"
            , data_end="##end_data##"
            , protect_begin="##begin_protect##"
            , protect_end="##end_protect##"
            ):
        self.beginComment = begin_comment
        self.endComment = end_comment
        self.eol = eol
        # le mode prefix seulement si le commentaire de fin c'est seulement la fin de ligne
        self.prefix_mode = False
        if self.endComment == self.eol:
            self.prefix_mode = True
        self.markupEntry = markup_entry
        self.scriptEntry = script_entry
        self.dataBegin = data_begin
        self.dataEnd = data_end
        self.protectBegin = protect_begin
        self.protectEnd = protect_end

    def setContent(self, sContent):
        self._content = sContent
        self._lines = []
        for l in self._content.split(self.eol):
            self._lines.append(Line(l, self))

    def getEndScriptIdx(self, idx):
        endContent = len(self._lines)
        while idx < endContent:
            if self._lines[idx].is_script_end:
                return idx
            idx += 1

    def getEndDataIdx(self, idx):
        endContent = len(self._lines)
        while idx < endContent:
            if self._lines[idx].is_data_end:
                return idx
            idx += 1

    def processContent2(self):
        outContent = []
        parts = []
        endContent = len(self._lines)
        idx = 0
        while idx < endContent:
            line = self._lines[idx]
            log.info(f"CONTENT: {idx}: {line}")
            if line.is_markup:
                # regarde si contient des données
                begin_idx = idx + 1
                while self._lines[begin_idx].is_data_begin:
                    end_idx = self.getEndDataIdx(begin_idx)
                    # traite les protected Area dans DataParts
                    parts.append(DataParts(self._lines, begin_idx, end_idx))
                    begin_idx = end_idx + 1
                idx = begin_idx
            elif line.is_script_begin:
                # script cherche la fin
                end_idx = self.getEndScriptIdx(idx)
                parts.append(ScriptParts(self._lines, idx, end_idx))
                idx = end_idx
            elif line.is_classical:
                # ligne classique
                end_idx = idx
                while self._lines[end_idx].is_classical:
                    end_idx += 1
                parts.append(ContentParts(self._lines, idx, end_idx - 1))
                idx = end_idx - 1
            idx += 1
        log.info(f"REPR {repr(parts)}")
        markupCtx = {}
        # index le contenu pour le contexte des scripts
        for p in parts:
            if type(p) is MarkupParts:
                markupCtx[p._name] = p
        log.info(f"Markup CTX {markupCtx}")
        # process le contenu en gérant le contexte pour les scripts parts afin que leur execution altère les parts
        self.pygen = ProxyClass(**{'log': log, 'markups': markupCtx,
                'globals': globals(),
                'locals': {},
            })
        for p in parts:
            p.process(outContent, self.pygen)
        log.info(f"CONTENT {repr(outContent)}")
        return self.eol.join(outContent)

    def processContent(self):
        outContent = []
        parts = []
        lineContent = self.content.split('\n')
        endContent = len(lineContent)
        idx = 0
        bg = -1
        while idx < endContent:
            log.info(f"CONTENT: {idx}: {lineContent[idx]}")
            if bg == -1:
                bg = idx
            # check markup
            hasMarkup = lineContent[idx].find(self.beginComment + self.markupEntry)
            if hasMarkup != -1:
                parts.append(ContentParts(lineContent, bg, idx - 1))
                bgMarkup = idx
                log.info(f"MARKUP FOUND")
                mk = re.compile(r'.*##markup##"(?P<markup_key>(?:\\.|[^"\\])+)"')
                # fixme: check le reste avant la fin du markup
                m = mk.match(lineContent[idx])
                if m is None:
                    raise RuntimeError(f"Parse error markup without key")
                g = m.groupdict()
                markup_key = g["markup_key"]
                log.info(f"KEY FOUND: {markup_key}")
                # markup at pos
                bgIdx, endIdx = -1, -1
                # contient possiblement une liste de data
                hasBegin = lineContent[idx+1].find(self.beginComment + self.dataBegin + self.endComment)
                if hasBegin != -1:
                    bgIdx = idx
                    # fixme: prendre tout le begin/data
                    while True:
                        # recup end
                        # fixme: check protected area
                        while idx < endContent:
                            # check une protected area
                            hasProtect = lineContent[idx].find(self.beginComment + self.protectedArea)
                            if hasProtect != -1:
                                protectBegin = idx
                                while idx < endContent:
                                    hasEnd = lineContent[idx].find(self.protectedArea + self.endComment)
                                    if hasEnd == -1:
                                        idx += 1
                                        continue
                                    protectedEnd = idx
                                # stocke la protected Area
                            # check la fin
                            hasEnd = lineContent[idx].find(self.beginComment + self.dataEnd + self.endComment)
                            if hasEnd == -1:
                                idx += 1
                                continue
                            endIdx = idx
                            break
                        #fixme: ajoute la partie
                        # ...
                        # recup new begin
                        hasBegin = lineContent[idx+1].find(self.beginComment + self.dataBegin + self.endComment)
                        if hasBegin == -1:
                            #parts.append(MarkupParts(lineContent, bgIdx, endIdx, markup_key))
                            break # stop la liste
                        bgIdx = idx
                    # liste de begin/end data ajouter à markup
                parts.append(MarkupParts(lineContent, bgMarkup, idx, markup_key))
                bg = idx + 1# nouveau taquet de reference apres le markup
                log.info(f"Add Markup Parts, reset bg {bg}")
            # check script
            hasScript = lineContent[idx].find(self.beginComment + self.scriptEntry)
            if hasScript != -1:
                log.info(f"MARKUP SCRIPT")
                # ajoute le block precedent comme etant du Content
                parts.append(ContentParts(lineContent, bg, idx - 1))
                beginScript = idx
                # cherche la fermeture du commentaire
                while idx < endContent:
                    hasEnded = lineContent[idx].find(self.endComment)
                    if hasEnded == -1:
                        idx += 1
                        continue
                    endScript = idx
                    break
                # fixme: stop script
                parts.append(ScriptParts(lineContent, beginScript, endScript))
                bg = idx + 1
            idx += 1
        log.info(f"END LOOP: {idx} / bg {bg} / endContent {endContent}")
        if bg != idx:
            parts.append(ContentParts(lineContent, bg, idx - 1))
        log.info(f"REPR {repr(parts)}")
        markupCtx = {}
        # index le contenu pour le contexte des scripts
        for p in parts:
            if type(p) is MarkupParts:
                markupCtx[p._name] = p
        log.info(f"Markup CTX {markupCtx}")
        # process le contenu en gérant le contexte pour les scripts parts afin que leur execution altère les parts
        self.pygen = ProxyClass(**{'log': log, 'markups': markupCtx,
                'globals': globals(),
                'locals': {},
            })
        for p in parts:
            p.process(outContent, self.pygen)
        log.info(f"CONTENT {repr(outContent)}")
        return self.eol.join(outContent)
