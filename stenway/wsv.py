from stenway.reliabletxt import *

class WsvChar:
	def isWhitespace(c):
		return (c == 0x09 or 
				(c >= 0x0B and c <= 0x0D) or
				c == 0x0020 or
				c == 0x0085 or
				c == 0x00A0 or
				c == 0x1680 or
				(c >= 0x2000 and c <= 0x200A) or
				c == 0x2028 or
				c == 0x2029 or
				c == 0x202F or
				c == 0x205F or
				c == 0x3000)
	
	def getWhitespaceCodePoints():
		return [0x0009,
			0x000B,
			0x000C,
			0x000D,
			0x0020,
			0x0085,
			0x00A0,
			0x1680,
			0x2000,
			0x2001,
			0x2002,
			0x2003,
			0x2004,
			0x2005,
			0x2006,
			0x2007,
			0x2008,
			0x2009,
			0x200A,
			0x2028,
			0x2029,
			0x202F,
			0x205F,
			0x3000]


class WsvString:
	def isWhitespace(str):
		if not str:
			return False
		codePoints = list(map(lambda c: ord(c), str))
		for c in codePoints:
			if not WsvChar.isWhitespace(c):
				return False
		return True


class WsvParserException(Exception):
	def __init__(self, index, lineIndex, linePosition, message):
		super().__init__("{} ({}, {})".format(message, lineIndex + 1, linePosition + 1))
		self.index = index
		self.lineIndex = lineIndex
		self.linePosition = linePosition


class WsvCharIterator(ReliableTxtCharIterator):
	def __init__(self, text):
		ReliableTxtCharIterator.__init__(self, text)
		
	def isWhitespace(self):
		if self.isEndOfText():
			return False
		return WsvChar.isWhitespace(self._chars[self._index])
	
	def getString(self, startIndex):
		part = self._chars[startIndex:self._index]
		return StringUtil.fromCodePoints(part)
	
	def readCommentText(self):
		startIndex = self._index
		while True:
			if self.isEndOfText():
				break
			if self._chars[self._index] == 0x0A:
				break
			self._index += 1
		
		return self.getString(startIndex)
		
	def skipCommentText(self):
		while True:
			if self.isEndOfText():
				break
			if self._chars[self._index] == 0x0A:
				break
			self._index += 1
	
	def readWhitespaceOrNull(self):
		startIndex = self._index
		while True:
			if self.isEndOfText():
				break
			c = self._chars[self._index]
			if c == 0x0A:
				break
			if not WsvChar.isWhitespace(c):
				break
			self._index += 1
		
		if self._index == startIndex:
			return None
		return self.getString(startIndex)
		
	def skipWhitespace(self):
		startIndex = self._index
		while True:
			if self.isEndOfText():
				break
			c = self._chars[self._index]
			if c == 0x0A:
				break
			if not WsvChar.isWhitespace(c):
				break
			self._index += 1
		
		return self._index > startIndex
	
	def getException(self, message):
		lineIndex, linePosition = self.getLineInfo()
		return WsvParserException(self._index, lineIndex, linePosition, message)
	
	def readString(self):
		chars = []
		while True:
			if self.isEndOfText() or self.isChar(0x0A):
				raise self.getException("String not closed")
			
			c = self._chars[self._index]
			if c == 0x22:
				self._index += 1
				if self.tryReadChar(0x22):
					chars.append(0x22)
				elif self.tryReadChar(0x2F):
					if not self.tryReadChar(0x22):
						raise self.getException("Invalid string line break")
					chars.append(0x0A)
				elif self.isWhitespace() or self.isChar(0x0A) or self.isChar(0x23) or self.isEndOfText():
					break
				else:
					raise self.getException("Invalid character after string")
			else:
				chars.append(c)
				self._index += 1
		
		return StringUtil.fromCodePoints(chars)
	
	def readValue(self):
		startIndex = self._index
		while True:
			if self.isEndOfText():
				break
			
			c = self._chars[self._index]
			if WsvChar.isWhitespace(c) or c == 0x0A or c == 0x23:
				break
			
			if c == 0x22:
				raise self.getException("Invalid double quote in value")
			
			self._index += 1
		
		if self._index == startIndex:
			raise self.getException("Invalid value")
		
		return self.getString(startIndex)


class WsvParser:
	def parseLineAsArray(content):
		iterator = WsvCharIterator(content)
		result = WsvParser._parseLineAsArray(iterator)
		if iterator.isChar(0x0A):
			raise iterator.getException("Multiple WSV lines not allowed")
		elif not iterator.isEndOfText():
			raise iterator.getException("Unexpected parser error")
		return result
		
	def _parseLineAsArray(iterator):
		iterator.skipWhitespace()
		values = []
		while (not iterator.isChar(0x0A)) and (not iterator.isEndOfText()):
			value = None
			if iterator.isChar(0x23):
				break
			elif iterator.tryReadChar(0x22):
				value = iterator.readString()
			else:
				value = iterator.readValue()
				if value == "-":
					value = None
			
			values.append(value)
			
			if not iterator.skipWhitespace():
				break
		
		if iterator.tryReadChar(0x23):
			iterator.skipCommentText()
		
		return values
	
	
	def parseDocumentAsJaggedArray(content):
		iterator = WsvCharIterator(content)
		lines = []
		
		while True:
			newLine = WsvParser._parseLineAsArray(iterator)
			lines.append(newLine)
			
			if iterator.isEndOfText():
				break
			elif not iterator.tryReadChar(0x0A):
				raise iterator.getException("Unexpected parser error")
		
		if not iterator.isEndOfText():
			raise iterator.getException("Unexpected parser error")
		return lines
	
	def parseLine(content):
		iterator = WsvCharIterator(content)
		result = WsvParser._parseLine(iterator)
		if iterator.isChar(0x0A):
			raise iterator.getException("Multiple WSV lines not allowed")
		elif not iterator.isEndOfText():
			raise iterator.getException("Unexpected parser error")
		return result
	
	def _parseLine(iterator):
		values = []
		whitespaces = []
		
		whitespace = iterator.readWhitespaceOrNull()
		whitespaces.append(whitespace)

		while (not iterator.isChar(0x0A)) and (not iterator.isEndOfText()):
			value = None
			if iterator.isChar(0x23):
				break
			elif iterator.tryReadChar(0x22):
				value = iterator.readString()
			else:
				value = iterator.readValue()
				if value == "-":
					value = None
				
			values.append(value)

			whitespace = iterator.readWhitespaceOrNull()
			if whitespace == None:
				break
			
			whitespaces.append(whitespace)
		
		comment = None
		if iterator.tryReadChar(0x23):
			comment = iterator.readCommentText()
			if whitespace == None:
				whitespaces.append(None)
		
		newLine = WsvLine(values)
		newLine._whitespaces = whitespaces
		newLine._comment = comment
		return newLine
	
	def parseDocument(content):
		document = WsvDocument()
		iterator = WsvCharIterator(content)
		
		while True:
			newLine = WsvParser._parseLine(iterator)
			document.addLine(newLine)
			
			if iterator.isEndOfText():
				break
			elif not iterator.tryReadChar(0x0A):
				raise iterator.getException("Unexpected parser error")
			
		if not iterator.isEndOfText():
			raise iterator.getException("Unexpected parser error")
		
		return document
	
	def parseLineNonPreserving(content):
		values = WsvParser.parseLineAsArray(content)
		return WsvLine(values)
		
	def parseDocumentNonPreserving(content):
		document = WsvDocument()
		iterator = WsvCharIterator(content)
		
		while True:
			lineValues = WsvParser._parseLineAsArray(iterator)
			newLine = WsvLine(lineValues)
			document.addLine(newLine)
			
			if iterator.isEndOfText():
				break
			elif not iterator.tryReadChar(0x0A):
				raise iterator.getException("Unexpected parser error")
		
		if not iterator.isEndOfText():
			raise iterator.getException("Unexpected parser error")
		
		return document


class WsvSerializer:
	def containsSpecialChar(value):
		chars = StringUtil.getCodePoints(value)
		for c in chars:
			if c == 0x0A or WsvChar.isWhitespace(c) or c == 0x22 or c == 0x23:
				return True
		return False
	
	def serializeValue(value):
		if value==None:
			return "-"
		elif len(value) == 0:
			return "\"\""
		elif value == "-":
			return "\"-\""
		elif WsvSerializer.containsSpecialChar(value):
			result = []
			chars = StringUtil.getCodePoints(value)
			result.append(0x22)
			for c in chars:
				if c == 0x0A:
					result.append(0x22)
					result.append(0x2F)
					result.append(0x22)
				elif c == 0x22:
					result.append(0x22)
					result.append(0x22)
				else:
					result.append(c)
			result.append(0x22)
			return StringUtil.fromCodePoints(result)
		else:
			return value
	
	def _serializeWhitespace(whitespace, isRequired):
		if whitespace != None and len(whitespace) > 0:
			return whitespace
		elif isRequired:
			return " "
		else:
			return ""
	
	def _serializeValuesWithWhitespace(line):
		result = ""
		whitespaces = line._whitespaces
		comment = line._comment
		if line.values == None:
			whitespace = whitespaces[0]
			result += WsvSerializer._serializeWhitespace(whitespace, False)
			return result
		
		for i in range(len(line.values)):
			whitespace = None
			if i < len(whitespaces):
				whitespace = whitespaces[i]
			
			if i == 0:
				result += WsvSerializer._serializeWhitespace(whitespace, False)
			else:
				result += WsvSerializer._serializeWhitespace(whitespace, True)
			
			result += WsvSerializer.serializeValue(line.values[i])
			
		if len(whitespaces) >= len(line.values) + 1:
			whitespace = whitespaces[len(line.values)]
			result += WsvSerializer._serializeWhitespace(whitespace, False)
		elif comment != None and len(line.Values) > 0:
			result += " "
		
		return result
	
	def _serializeValuesWithoutWhitespace(line):
		result = ""
		if line.values == None:
			return result
		
		isFollowingValue = False
		for value in line.values:
			if isFollowingValue:
				result += ' '
			else:
				isFollowingValue = True
			
			result += WsvSerializer.serializeValue(value)
		
		if line.getComment() != None and len(line.values) > 0:
			result += " "
		
		return result
	
	def serializeLine(line):
		result = ""
		whitespaces = line._whitespaces
		if whitespaces != None and len(whitespaces) > 0:
			result += WsvSerializer._serializeValuesWithWhitespace(line)
		else:
			result += WsvSerializer._serializeValuesWithoutWhitespace(line)
		
		comment = line._comment
		if comment != None:
			result += "#"
			result += comment
		
		return result
	
	def serializeLineValues(values):
		result = ""
		isFirstValue = True
		for value in values:
			if not isFirstValue:
				result += " "
			else:
				isFirstValue = False
			
			result += WsvSerializer.serializeValue(value)
		
		return result
	
	def serializeLineNonPreserving(line):
		return WsvSerializer.serializeLineValues(line.values)
		
	def serializeDocument(document):
		result = ""
		isFirstLine = True
		for line in document.lines:
			if not isFirstLine:
				result += "\n"
			else:
				isFirstLine = False
			
			result += WsvSerializer.serializeLine(line)
		
		return result
	
	def serializeDocumentNonPreserving(document):
		result = ""
		isFirstLine = True
		for line in document.lines:
			if not isFirstLine:
				result += "\n"
			else:
				isFirstLine = False
			
			result += WsvSerializer.serializeLineNonPreserving(line)
		
		return result


class WsvLine:
	def __init__(self, values=None, whitespaces=None, comment=None):
		if values is None:
			self.values = []
		else:
			self.values = values
		self.setWhitespaces(whitespaces)
		self.setComment(comment)
	
	def hasValues(self):
		return self.values != None and len(self.values) > 0
		
	def setWhitespaces(self, whitespaces):
		WsvLine.validateWhitespaces(whitespaces)
		self._whitespaces = whitespaces
		
	def setComment(self, comment):
		WsvLine.validateComment(comment)
		self._comment = comment
		
	def setValues(self, *values):
		self.values = []
		for value in values:
			self.values.append(value)
		
	def validateWhitespaces(whitespaces):
		if whitespaces != None:
			for whitespace in whitespaces:
				if whitespace != None and len(whitespace) > 0 and not WsvString.isWhitespace(whitespace):
					raise Exception("Whitespace value contains non whitespace character or line feed")
	
	def validateComment(comment):
		if comment != None and comment.find('\n') >= 0:
			raise Exception("Line feed in comment is not allowed")
	
	def getWhitespaces(self):
		return self._whitespaces
	
	def getComment(self):
		return self._comment
	
	def parse(content, preserveWhitespaceAndComment = True):
		if preserveWhitespaceAndComment:
			return WsvParser.parseLine(content)
		else:
			return WsvParser.parseLineNonPreserving(content)
	
	def parseAsArray(content):
		return WsvParser.parseLineAsArray(content)
	
	def __str__(self):
		return self.toString(True)
		
	def toString(self, preserveWhitespaceAndComment):
		if preserveWhitespaceAndComment:
			return WsvSerializer.serializeLine(self)
		else:
			return WsvSerializer.serializeLineNonPreserving(self)
	
	def _set(self, values, whitespaces, comment):
		self.values = values
		self._whitespaces = whitespaces
		self._comment = comment


class WsvDocument:
	def __init__(self, lines = None, encoding = ReliableTxtEncoding.UTF_8):
		if lines is None:
			self.lines = []
		else:
			self.lines = lines
		self.encoding = encoding
	
	def setEncoding(self, encoding):
		self.encoding = encoding
		
	def getEncoding(self):
		return self.encoding
		
	def addLine(self, line):
		self.lines.append(line)
		
	def __str__(self):
		return self.toString()
		
	def toString(self, preserveWhitespaceAndComments=True):
		if preserveWhitespaceAndComments:
			return WsvSerializer.serializeDocument(self)
		else:
			return WsvSerializer.serializeDocumentNonPreserving(self)
	
	def toArray(self):
		array = []
		for line in self.lines:
			array.append(line.values)
		return array
		
	def save(self, filePath, preserveWhitespaceAndComments=True):
		content = self.toString(preserveWhitespaceAndComments)
		file = ReliableTxtDocument(content, self.encoding)
		file.save(filePath)
		
	def parse(content, preserveWhitespaceAndComments=True):
		if preserveWhitespaceAndComments:
			return WsvParser.parseDocument(content)
		else:
			return WsvParser.parseDocumentNonPreserving(content)
		
	def load(filePath, preserveWhitespaceAndComments=True):
		file = ReliableTxtDocument.load(filePath)
		content = file.getText()
		document = WsvDocument.parse(content, preserveWhitespaceAndComments)
		document.setEncoding(file.getEncoding())
		return document
	
	def parseAsJaggedArray(content):
		return WsvParser.parseDocumentAsJaggedArray(content)
