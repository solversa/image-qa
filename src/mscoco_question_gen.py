import os
import subprocess
import time
import re
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet

parseFilename = '../../../data/mscoco/mscoco_caption.parse.txt'
lemmatizer = WordNetLemmatizer()

class TreeNode:
    def __init__(self, className, text, children, level):
        self.className = className
        self.text = text
        self.children = children
        self.level = level
        pass
    def __str__(self):
        strlist = []
        for i in range(self.level):
            strlist.append('    ')
        strlist.extend(['(', self.className])
        if len(self.children) > 0:
            strlist.append('\n')
            for child in self.children:
                strlist.append(child.__str__())
            if len(self.text) > 0:
                for i in range(self.level + 1):
                    strlist.append('    ')
            else:
                for i in range(self.level):
                    strlist.append('    ')
        else:
            strlist.append(' ')
        strlist.append(self.text)
        strlist.append(')\n')
        return ''.join(strlist)
    def toSentence(self):
        strlist = []
        for child in self.children:
            childSent = child.toSentence()
            if len(childSent) > 0:
                strlist.append(childSent)
        if len(self.text) > 0:
            strlist.append(self.text)
        return ' '.join(strlist)
    def relevel(self,level):
        self.level = level
        for child in self.children:
            child.relevel(level + 1)
    def copy(self):
        children = []
        for child in self.children:
            children.append(child.copy())
        return TreeNode(self.className, self.text, children, self.level)

class QuestionGenerator:
    def __init__(self):
        self.lexnameDict = {}
        pass

    @staticmethod
    def escapeNumber(line):
        line = re.sub('^11$', 'eleven', line)
        line = re.sub('^12$', 'twelve', line)
        line = re.sub('^13$', 'thirteen', line)
        line = re.sub('^14$', 'fourteen', line)
        line = re.sub('^15$', 'fifteen', line)
        line = re.sub('^16$', 'sixteen', line)
        line = re.sub('^17$', 'seventeen', line)
        line = re.sub('^18$', 'eighteen', line)
        line = re.sub('^19$', 'nineteen', line)
        line = re.sub('^20$', 'twenty', line)
        line = re.sub('^10$', 'ten', line)
        line = re.sub('^0$', 'zero', line)
        line = re.sub('^1$', 'one', line)
        line = re.sub('^2$', 'two', line)
        line = re.sub('^3$', 'three', line)
        line = re.sub('^4$', 'four', line)
        line = re.sub('^5$', 'five', line)
        line = re.sub('^6$', 'six', line)
        line = re.sub('^7$', 'seven', line)
        line = re.sub('^8$', 'eight', line)
        line = re.sub('^9$', 'nine', line)
        return line

    def whMovement(self, root):
        #print 'Original:', root
        stack = [[]] # A hack for closure support
        found = [False]
        def traverseFindTopClass(node, className):
            if not found[0]:
                stack[0].append(node)
                if node.className == className:
                    found[0] = True
                else:
                    for child in node.children:
                        traverseFindTopClass(child, className)
                    if not found[0]:
                        del stack[0][-1]

        # Find the subject (first NP) and change determiner to 'the'
        traverseFindTopClass(root, 'NP')
        if found[0]:
            np = stack[0][-1]
            while np.className != 'DT' and len(np.children) > 0:
                np = np.children[0]
            if np.className == 'DT':
                np.text = 'the'

        # First look for the position of WHNP
        found[0] = False
        stack[0] = []
        traverseFindTopClass(root, 'WHNP')
        if not found[0]: 
            return False

        # Check if the WHNP is inside an SBAR, not handling this case for now.
        insideSBar = False
        # Check if inside NP, violates A-over-A principal
        insideNP = False

        whStack = stack[0][:]
        whPosition = len(whStack) - 1

        for item in whStack:
            #print item.className,
            if item.className == 'SBAR':
                insideSBar = True
            if item.className == 'NP':
                insideNP = True
                # Testing
                whPosition = whStack.index(item)

        node = root
        parent = root
        while len(node.children) > 0:
            parent = node
            node = node.children[0]
        if parent.className == 'WHNP':
        #if root.toSentence().startswith('how many'):
            print 'WH already at the front'
            return False
        else:
            print 'The first node is ' + parent.className
            print root
        if insideSBar:
            #print 'Inside SBar'
            return False
        # if insideNP:
        #     #print 'Inside NP'
        #     return False


        # Look for VP
        found[0] = False
        stack[0] = []
        traverseFindTopClass(root, 'VP')

        if not found[0]:
            print 'Not found VP'
            return True
        else:
            vpnode = stack[0][-1]
            vpchild = vpnode.children[0]
            frontWord = None
            if vpchild.className == 'VBZ': # is, has, singular present
                if vpchild.text == 'is':
                    frontWord = vpchild
                    vpnode.children.remove(vpchild)
                elif vpchild.text == 'has': # Could be has something or has done
                    done = False
                    for child in vpnode.children:
                        if child.className == 'VP':
                            done = True
                            break
                    if done:
                        frontWord = vpchild
                        vpnode.children.remove(vpchild)
                    else:
                        frontWord = TreeNode('VBZ', 'does', [], 0)
                        vpchild.text = 'have'
                        vpchild.className = 'VB'
                else:
                    # need to lemmatize the verb and separate does
                    frontWord = TreeNode('VBZ', 'does', [], 0)
                    vpchild.className = 'VB'
                    vpchild.text = lemmatizer.lemmatize(vpchild.text, 'v')
                pass
            elif vpchild.className == 'VBP': # do, have, present
                if vpchild.text == 'are':
                    frontWord = vpchild
                    vpnode.children.remove(vpchild)
                else:    
                    frontWord = TreeNode('VBP', 'do', [], 0)
                    vpchild.className = 'VB'
                pass
            elif vpchild.className == 'VBD': # did, past tense
                if vpchild.text == 'was' or vpchild.text == 'were':
                    frontWord = vpchild
                    vpnode.children.remove(vpchild)
                elif vpchild.text == 'had': # Could be had something or had done
                    done = False
                    for child in vpnode.children:
                        if child.className == 'VP':
                            done = True
                            break
                    if done:
                        frontWord = vpchild
                        vpnode.children.remove(vpchild)
                    else:
                        frontWord = TreeNode('VBD', 'did', [], 0)
                        vpchild.text = 'have'
                        vpchild.className = 'VB'
                else:
                    # need to lemmatize the verb and separate did
                    frontWord = TreeNode('VBD', 'did', [], 0)
                    vpchild.className = 'VB'
                    vpchild.text = lemmatizer.lemmatize(vpchild.text, 'v')
                pass
            elif vpchild.className == 'MD': # will, may, shall
                frontWord = vpchild
                vpnode.children.remove(vpchild)
                pass
            if frontWord is not None:
                # Remove WHNP from its parent
                whStack[whPosition-1].children.remove(whStack[whPosition])
                bigS = TreeNode('S', '', [whStack[-1], stack[0][1]], 0)
                stack[0][0].children = [bigS]
                bigS.children[1].children.insert(0, frontWord)
            else:
                print 'Not found front word'


        # reassign levels to the new tree
        root.relevel(0)
        #print 'WH-movement'
        return True
        #print 'WH-movement:', root

    def splitCCStructure(self, root):
        # Find (ROOT (S ...) (CC ...) (S ...)) structure and split them into separate trees.
        # Issue: need to resolve coreference in the later sentences.
        roots = []
        node = root.children[0] # directly search for the top-most S.
        if node.className == 'S':
            if len(node.children) >= 3:
                childrenClasses = []
                for child in node.children:
                    childrenClasses.append(child.className)
                renew = True
                index = 0
                for c in childrenClasses:
                    if c == 'S' and renew:
                        root_ = TreeNode('ROOT', '', [node.children[index]], 0)
                        root_.relevel(0)
                        roots.append(root_)
                    elif c == 'CC':
                        renew = True
                    index += 1
        if len(roots) == 0:
            roots.append(root)
        return roots

    def lookupLexname(self, word):
        if self.lexnameDict.has_key(word):
            return self.lexnameDict[word]
        else:
            synsets = wordnet.synsets(word) # Just pick the first definition
            if len(synsets) > 0:
                self.lexnameDict[word] = synsets[0].lexname()
                return self.lexnameDict[word]
            else:
                return None

    def askWhoWhat(self, root):
        found = [False] # A hack for closure support in python 2.7
        answer = ['']
        rootsReplaceWhat = [[]] # Unlike in 'how many', here we enumerate all possible 'what's
        def traverse(node):
            for child in node.children:
                traverse(child)
            if node.className == 'NP':
                replace = False
                whword = ''
                for child in node.children:
                    if child.className == 'NN' or child.className == 'NNS':
                        lexname = self.lookupLexname(child.text)
                        if lexname is not None:
                            if lexname == 'noun.person':
                                whword = 'who'
                            else:
                                whword = 'what'
                            answer[0] = child.text
                            found[0] = True
                            replace = True
                if replace:
                    what = TreeNode('WP', whword, [], node.level + 1)
                    children = [what]
                    children_bak = node.children
                    node.children = children
                    node.className = 'WHNP'
                    copy = root.copy()
                    copy.answer = answer[0]
                    rootsReplaceWhat[0].append(copy)
                    node.className = 'NP'
                    node.children = children_bak

        rootsSplitCC = self.splitCCStructure(root)
        for r in rootsSplitCC:
            traverse(r)
            for r2 in rootsReplaceWhat[0]:
                if r2.children[0].children[-1].className != '.':
                    r2.children[0].children.append(TreeNode('.', '?', [], 2))
                else:
                    r2.children[0].children[-1].text = '?'
                if found[0]:
                    self.whMovement(r2)
                    yield (r2.toSentence().lower(), self.escapeNumber(r2.answer.lower()))
                else:
                    pass
            found[0] = False
            answer[0] = ''
            rootsReplaceWhat[0] = []

    def askHowMany(self, root):
        found = [False] # A hack for closure support in python 2.7
        answer = ['']
        def traverse(node):
            if not found[0]:
                for child in node.children:
                    traverse(child)
                if node.className == 'NP':
                    #obj = None
                    count = None
                    for child in node.children:
                        if child.className == 'CD':
                            found[0] = True
                            answer[0] = child.text
                            count = child
                    if found[0] and count is not None:
                        how = TreeNode('WRB', 'how', [], node.level + 2)
                        many = TreeNode('JJ', 'many', [], node.level + 2)
                        howmany = TreeNode('WHNP', '', [how, many], node.level + 1)
                        children = [howmany]
                        children.extend(node.children[node.children.index(count)+1:])
                        #node.children.remove(count)
                        node.children = children
                        node.className = 'WHNP'

        roots = self.splitCCStructure(root)

        for r in roots:
            traverse(r)
            if r.children[0].children[-1].className != '.':
                r.children[0].children.append(TreeNode('.', '?', [], 2))
            else:
                r2.children[0].children[-1].text = '?'
            if found[0]:
                self.whMovement(r)
                yield (r.toSentence().lower(), self.escapeNumber(answer[0].lower()))
            else:
                pass
                #return None
            found[0] = False
            answer[0] = ''

    def ask(self, root):
        pass

def stanfordParse(sentence):
    with open('tmp.txt', 'w+') as f:
        f.write(sentence)
    with open('tmpout.txt', 'w+') as fout:
        subprocess.call(['../../../tools/stanford-parser-full-2015-01-30/lexparser.sh', 'tmp.txt'], stdout=fout)
    with open('tmpout.txt') as f:
        result = f.read()
    os.remove('tmp.txt')
    os.remove('tmpout.txt')
    return result

# Finite state machine implementation of syntax tree parser.
class TreeParser:
    def __init__(self):
        self.state = 0
        self.currentClassStart = 0
        self.currentTextStart = 0
        self.classNameStack = []
        self.childrenStack = [[]]
        self.root = None
        self.rootsList = []
        self.level = 0
        self.stateTable = [self.state0,self.state1,self.state2,self.state3,self.state4,self.state5,self.state6]
        self.raw = None
        self.state = 0

    def parse(self, raw):
        if not self.isAlpha(raw[0]):
            self.raw = raw
            for i in range(len(raw)):
                self.state = self.stateTable[self.state](i)

    @staticmethod
    def isAlpha(c):
        return 65 <= ord(c) <= 90 or 97 <= ord(c) <= 122

    @staticmethod
    def isNumber(c):
        return 48 <= ord(c) <= 57

    @staticmethod
    def exception(raw, i):
        print raw
        raise Exception(
            'Unexpected character "%c" (%d) at position %d' \
            % (raw[i], ord(raw[i]), i))

    @staticmethod
    def isClassName(s):
        if TreeParser.isAlpha(s) or s == '.' or s == ',' or s == '$' or s == '\'' or s == '`' or s == ':' or s == '-' or s == '#':
            return True
        else:
            return False

    @staticmethod
    def isText(s):
        if TreeParser.isAlpha(s) or TreeParser.isNumber(s) or s == '.' or s == ',' or s == '-' or s == '\'' or s == '`' or s == '/' or s == '>' or s == ':' or s == ';' or s == '\\' or s == '!' or s == '?' or s == '&' or s == '-' or s == '=' or s == '#' or s == '$' or s == '@' or s == '_' or s == '*' or s == '+' or s == chr(194) or s == chr(160):
            return True
        else:
            return False 

    def state0(self, i):
        if self.raw[i] == '(':
            return 1
        else:
            return 0

    def state1(self, i):
        if self.isClassName(self.raw[i]):
            #global currentClassStart, level, childrenStack
            self.currentClassStart = i
            self.level += 1
            self.childrenStack.append([])
            return 2
        else:
            self.exception(self.raw, i)

    def state2(self, i):
        if self.isClassName(self.raw[i]):
            return 2
        else:
            #global classNameStack
            self.classNameStack.append(self.raw[self.currentClassStart:i])
            if self.raw[i] == ' ' and self.raw[i + 1] == '(':
                return 0
            elif self.raw[i] == ' ' and self.isText(self.raw[i + 1]):
                return 4
            elif self.raw[i] == '\n':
                return 3
            else:
                self.exception(self.raw, i)

    def state3(self, i):
        if self.raw[i] == ' ' and self.raw[i + 1] == '(':
            return 0
        elif self.raw[i] == ' ' and self.raw[i + 1] == ' ':
            return 3
        elif self.raw[i] == ' ' and self.isText(self.raw[i + 1]):
            return 4
        else:
            return 3

    def state4(self, i):
        if self.isText(self.raw[i]):
            #global currentTextStart
            self.currentTextStart = i
            return 5
        else:
            self.exception(self.raw, i)

    def state5(self, i):
        if self.isText(self.raw[i]):
            return 5
        elif i == len(self.raw) - 1:
            return 5
        elif self.raw[i] == ')':
            self.wrapup(self.raw[self.currentTextStart:i])
            if self.level == 0:
                return 0
            elif self.raw[i + 1] == ')':
                return 6
            else:
                return 3
        else:
            self.exception(self.raw, i)

    def state6(self, i):
        if self.level == 0:
            return 0
        elif self.raw[i] == ')':
            self.wrapup('')
            return 6
        else:
            return 3

    def wrapup(self, text):
        #global childrenStack, root, self.level, rootsList
        self.level -= 1
        root = TreeNode(self.classNameStack[-1], text, self.childrenStack[-1][:], self.level)
        del self.childrenStack[-1]
        del self.classNameStack[-1]
        self.childrenStack[-1].append(root)
        if self.level == 0:
            self.rootsList.append(root)
            # print 'Parsed tree:'
            # print root

def questionGen():
    startTime = time.time()
    questionCount = 0
    numSentences = 0
    parser = TreeParser()
    gen = QuestionGenerator()
    with open(parseFilename) as f:
        for line in f:
            if len(parser.rootsList) > 0:
                #print rootsList[0]
                numSentences += 1
                originalSent = parser.rootsList[0].toSentence()
                #qaiter = gen.askHowMany(parser.rootsList[0])
                qaiter = gen.askWhoWhat(parser.rootsList[0])
                hasItem = False
                for qaitem in qaiter:
                    questionCount += 1
                    hasItem = True
                    print ('Question %d:' % questionCount), qaitem[0], 'Answer:', qaitem[1]
                if hasItem:
                    print 'Original:', originalSent
                del(parser.rootsList[0])
                if questionCount > 500:
                    break
            parser.parse(line)
    # Approx. 3447.5 sentences per second
    print 'Number of sentences parsed:', numSentences
    print 'Number of seconds:', time.time() - startTime

def testHook():
    #s = stanfordParse('There are two ovens in a kitchen restaurant , and one of them is being used .')
    #s = stanfordParse('A bathroom with two sinks a bathtub and a shower with lots of lighting from the windows .')
    #s = stanfordParse('A man waits at the crosswalk with his bicycle .')
    s = stanfordParse('A black cat sits on a bathroom floor next to some laundry .')



    #print s
    s = s.split('\n')
    parser = TreeParser()
    gen = QuestionGenerator()
    for i in range(len(s)):
        #print s[i]
        parser.parse(s[i] + '\n')
    tree = parser.rootsList[0]
    #print tree
    qaiter = gen.askWhoWhat(tree)
    for qaitem in qaiter:
        print ('Question:'), qaitem[0], 'Answer:', qaitem[1]

if __name__ == '__main__':
    testHook()
    #questionGen()


