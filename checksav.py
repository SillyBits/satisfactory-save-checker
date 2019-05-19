#!/usr/bin/env python3
"""
Checks Satisfactory save games for containing invalid objects.

Based on bitowl's sav2json.py (https://github.com/bitowl/satisfactory-save-format)
with json export being replaced by validity checkers.
"""

import struct
import functools
import itertools
import csv
import binascii
import sys
import argparse
import pathlib
import math


parser = argparse.ArgumentParser(
	description='Checks Satisfactory save games for containing invalid objects')
parser.add_argument('file', metavar='FILE', type=str,
					help='save game to process (.sav file extension)')
parser.add_argument('--verbose', '-v', help='verbose output', action='store_true')

args = parser.parse_args()

extension = pathlib.Path(args.file).suffix
if extension != '.sav':
	print('error: extension of save file should be .sav', file=sys.stderr)
	exit(1)

f = open(args.file, 'rb')

# determine the file size so that we can
f.seek(0, 2)
fileSize = f.tell()
f.seek(0, 0)

bytesRead = 0


def assertFail(message):
	print('assertion failed: ' + message, file=sys.stderr)
	# show the next bytes to help debugging
	print(readHex(32))
	input()
	assert False


def readInt():
	global bytesRead
	bytesRead += 4
	return struct.unpack('i', f.read(4))[0]


def readFloat():
	global bytesRead
	bytesRead += 4
	return struct.unpack('f', f.read(4))[0]


def readLong():
	global bytesRead
	bytesRead += 8
	return struct.unpack('q', f.read(8))[0]


def readByte():
	global bytesRead
	bytesRead += 1
	return struct.unpack('b', f.read(1))[0]


def assertNullByte():
	global bytesRead
	bytesRead += 1
	zero = f.read(1)
	if zero != b'\x00':
		assertFail('not null but ' + str(zero))


def readLengthPrefixedString():
	"""
	Reads a string that is prefixed with its length
	"""
	global bytesRead
	length = readInt()
	
	sz = ""

	if length < 0:
	    # Read unicode string
		
		length = length * -2

		try:
			chars = f.read(length-2)
		except:
			assertFail("Error reading string at pos {} with length {}".format(f.tell(), length))

		zero = f.read(2)
		bytesRead += length

		if zero != b'\x00\x00':  # We assume that the last byte of a string is alway \x00
			if length > 100:
				assertFail('zero is ' + str(zero) + ' in ' + str(chars[0:100]))
			else:
				assertFail('zero is ' + str(zero) + ' in ' + str(chars))
		sz = chars.decode('utf-16')

	elif length > 0:
		# Read 8bit-ASCII
		
		try:
			chars = f.read(length-1)
		except:
			assertFail("Error reading string at pos {} with length {}".format(f.tell(), length))

		zero = f.read(1)
		bytesRead += length

		if zero != b'\x00':  # We assume that the last byte of a string is alway \x00
			if length > 100:
				assertFail('zero is ' + str(zero) + ' in ' + str(chars[0:100]))
			else:
				assertFail('zero is ' + str(zero) + ' in ' + str(chars))
		sz = chars.decode('ascii')

	return sz

def readHex(count):
	"""
	Reads count bytes and returns their hex form
	"""
	global bytesRead
	bytesRead += count

	chars = f.read(count)
	c = 0
	result = ''
	for i in chars:
		result += format(i, '02x') + ' '
		c += 1
		if (c % 4 == 0 and c < count - 1):
			result += ' '

	return result


"""
Actual error checking
"""

errors = []

LOWER_BOUND = -1.0e+10
UPPER_BOUND = +1.0e+10

def isValid(val, lowerbounds=None, upperbounds=None):
	#global LOWER_BOUND, UPPER_BOUND
	if val is None or val == math.inf or val == math.nan:
		return False
	limit = lowerbounds or LOWER_BOUND
	if val <= limit:
		return False
	limit = upperbounds or UPPER_BOUND
	if val >= limit:
		return False
	return True
	
def isValidVec3(a,b,c, lowerbounds=None, upperbounds=None):
	return  isValid(a, lowerbounds, upperbounds)\
		and isValid(b, lowerbounds, upperbounds)\
		and	isValid(c, lowerbounds, upperbounds)
	
def isValidVec4(a,b,c,d, lowerbounds=None, upperbounds=None):
	return  isValid(a, lowerbounds, upperbounds)\
		and isValid(b, lowerbounds, upperbounds)\
		and	isValid(c, lowerbounds, upperbounds)\
		and	isValid(d, lowerbounds, upperbounds)

	
def addError(desc):	
	errors.append(desc)
	
	if 'pathName' in desc:
		print("\n- pathName='{}'".format(desc['pathName']))
	#elif 'name' in desc: # We'll have to see if this holds enough info for finding it later on, meawhile: print all
	#	print("\n- name='{}'".format(desc['name']))
	else:
		print("\n- Object {}".format(desc))

def checkRot(desc, a,b,c,d=None):
	if d is None:
		if not isValidVec3(a,b,c):
			addError(desc)
			print("\t-> Invalid rot: {} | {} | {}".format(a,b,c))
			return False
	else:
		if not isValidVec4(a,b,c,d):
			addError(desc)
			print("\t-> Invalid rot: {} | {} | {} | {}".format(a,b,c,d))
			return False
	return True

def checkTrans(desc, x,y,z):
	if not isValidVec3(x,y,z):
		addError(desc)
		print("\t-> Invalid trans: {} | {} | {}".format(x,y,z))
		return False
	return True

def checkScale(desc, sx,sy,sz):
	if not isValidVec3(sx,sy,sz, 1.0e-10): # For now, we do ignore negative scales and let them print as errors
		addError(desc)
		print("\t-> Invalid scale: {} | {} | {}".format(sx,sy,sz))
		return False
	return True
		


# Read the file header
saveHeaderType = readInt()
saveVersion = readInt()  # Save Version
buildVersion = readInt()  # BuildVersion

mapName = readLengthPrefixedString()  # MapName
mapOptions = readLengthPrefixedString()  # MapOptions
sessionName = readLengthPrefixedString()  # SessionName
playDurationSeconds = readInt()  # PlayDurationSeconds

saveDateTime = readLong()  # SaveDateTime
'''
to convert this FDateTime to a unix timestamp use:
saveDateSeconds = saveDateTime / 10000000
# see https://stackoverflow.com/a/1628018
print(saveDateSeconds-62135596800)
'''
sessionVisibility = readByte()  # SessionVisibility

entryCount = readInt()  # total entries
hierarchy = {
	'saveHeaderType': saveHeaderType,
	'saveVersion': saveVersion,
	'buildVersion': buildVersion,
	'mapName': mapName,
	'mapOptions': mapOptions,
	'sessionName': sessionName,
	'playDurationSeconds': playDurationSeconds,
	'saveDateTime': saveDateTime,
	'sessionVisibility': sessionVisibility,
	'objects': [],
	'collected': []
}


def readActor():
	className = readLengthPrefixedString()
	levelName = readLengthPrefixedString()
	pathName = readLengthPrefixedString()
	needTransform = readInt()

	a = readFloat()
	b = readFloat()
	c = readFloat()
	d = readFloat()
	x = readFloat()
	y = readFloat()
	z = readFloat()
	sx = readFloat()
	sy = readFloat()
	sz = readFloat()

	wasPlacedInLevel = readInt()


	desc = {
		'className': className,
		'levelName': levelName,
		'pathName': pathName,
	}
	overallCheckState  = checkRot  (desc, a,b,c,d)
	overallCheckState &= checkTrans(desc, x,y,z)
	overallCheckState &= checkScale(desc, sx,sy,sz)
	
	return {
		'type': 1,
		'className': className,
		'levelName': levelName,
		'pathName': pathName,
		'needTransform': needTransform,
		'transform': {
			'rotation': [a, b, c, d],
			'translation': [x, y, z],
			'scale3d': [sx, sy, sz],

		},
		'wasPlacedInLevel': wasPlacedInLevel
	},overallCheckState


def readObject():
	className = readLengthPrefixedString()
	levelName = readLengthPrefixedString()
	pathName = readLengthPrefixedString()
	outerPathName = readLengthPrefixedString()

	return {
		'type': 0,
		'className': className,
		'levelName': levelName,
		'pathName': pathName,
		'outerPathName': outerPathName
	},True#overallCheckState


for i in range(0, entryCount):
	type = readInt()
	obj = None
	overallCheckState = True
	if type == 1:
		obj,overallCheckState = readActor()
		if not overallCheckState:
			print("  in actor, pathName='{pathName}', className='{className}'".format(**obj))
	elif type == 0:
		obj,overallCheckState = readObject()
		if not overallCheckState:
			print("  in object, pathName='{pathName}', outerPathName='{outerPathName}'".format(**obj))
	else:
		assertFail('unknown type {} at filepos {}'.format(type, ftell(f)-4))
	hierarchy['objects'].append(obj)


elementCount = readInt()

# So far these counts have always been the same and the entities seem to belong 1 to 1 to the actors/objects read above
if elementCount != entryCount:
	assertFail('elementCount ('+str(elementCount) +
			   ') != entryCount('+str(entryCount)+')')


def readProperty(properties):
	overallCheckState = True

	name = readLengthPrefixedString()
	if name == 'None':
		return

	prop = readLengthPrefixedString()
	length = readInt()
	index = readInt()

	property = {
		'name': name,
		'type': prop,
		'_length': length,
	    'index': index
	}

	if prop == 'IntProperty':
		assertNullByte()
		property['value'] = readInt()

	elif prop == 'StrProperty':
		assertNullByte()
		property['value'] = readLengthPrefixedString()

	elif prop == 'StructProperty':
		type = readLengthPrefixedString()

		property['structUnknown'] = readHex(17)  # TODO

		if type == 'Vector' or type == 'Rotator':
			x = readFloat()
			y = readFloat()
			z = readFloat()
			property['value'] = {
				'type': type,
				'x': x,
				'y': y,
				'z': z
			}
			if type == 'Vector':
				overallCheckState &= checkTrans(property, x,y,z)
			else:
				overallCheckState &= checkRot(property, x,y,z)
			if not overallCheckState:
				print("  in StructProperty.{}".format(type))
				
		elif type == 'Box':
			minX = readFloat()
			minY = readFloat()
			minZ = readFloat()
			maxX = readFloat()
			maxY = readFloat()
			maxZ = readFloat()
			isValid = readByte()
			property['value'] = {
				'type': type,
				'min': [minX, minY, minZ],
				'max': [maxX, maxY, maxZ],
				'isValid': isValid
			}
			#TODO: Add checking corners
			
		elif type == 'LinearColor':
			r = readFloat()
			g = readFloat()
			b = readFloat()
			a = readFloat()
			property['value'] = {
				'type': type,
				'r': r,
				'g': g,
				'b': b,
				'a': a
			}
			#INVESTIGATE: Invalid colors even came up as an issue yet?
			
		elif type == 'Transform':
			props = []
			#TODO: Add checkers
			#while (readProperty(props)):
			#	pass
			while (True):
				t = readProperty(props)
				if not t or not t[0]:
					break
				if not t[1]:
					print("  in StructProperty.Transform[{}]".format(len(props)))
					overallCheckState = False
			#if overallCheckState == False:
			#	print("  at name='{}', type='{}'".format(property['name'], property['type']))
			
			property['value'] = {
				'type': type,
				'properties': props
			}

		elif type == 'Quat':
			a = readFloat()
			b = readFloat()
			c = readFloat()
			d = readFloat()
			property['value'] = {
				'type': type,
				'a': a,
				'b': b,
				'c': c,
				'd': d
			}
			overallCheckState &= checkRot(property, a,b,c,d)
			if not overallCheckState:
				print("  in StructProperty.Quat")

		elif type == 'RemovedInstanceArray' or type == 'InventoryStack':
			props = []
			#TODO: Add checkers
			#while (readProperty(props)):
			#	pass
			while (True):
				t = readProperty(props)
				if not t or not t[0]:
					break
				if not t[1]:
					print("  in {}[{}]".format(type, len(props)))
					overallCheckState = False
			#if overallCheckState == False:
			#	print("  at name='{}', type='{}'".format(property['name'], property['type']))

			property['value'] = {
				'type': type,
				'properties': props
			}
			
		elif type == 'InventoryItem':
			unk1 = readLengthPrefixedString()  # TODO
			itemName = readLengthPrefixedString()
			levelName = readLengthPrefixedString()
			pathName = readLengthPrefixedString()

			props = []
			#TODO: Add checkers
			#readProperty(props)
			t = readProperty(props)
			if t and not t[1]:
				print("  in StructProperty.InventoryItem, itemName='{}'".format(itemName))
				overallCheckState = False
			
			# can't consume null here because it is needed by the entaingling struct

			property['value'] = {
				'type': type,
				'unk1': unk1,
				'itemName': itemName,
				'levelName': levelName,
				'pathName': pathName,
				'properties': props
			}
			
		else:
			assertFail('Unknown type: ' + type)

	elif prop == 'ArrayProperty':
		itemType = readLengthPrefixedString()
		assertNullByte()
		count = readInt()
		values = []

		if itemType == 'ObjectProperty':
			for j in range(0, count):
				values.append({
					'levelName': readLengthPrefixedString(),
					'pathName': readLengthPrefixedString()
				})
				
		elif itemType == 'StructProperty':
			structName = readLengthPrefixedString()
			structType = readLengthPrefixedString()
			structSize = readInt()
			zero = readInt()
			if zero != 0:
				assertFail('not zero: ' + str(zero))

			type = readLengthPrefixedString()

			property['structName'] = structName
			property['structType'] = structType
			property['structInnerType'] = type

			property['structUnknown'] = readHex(17)  # TODO what are those?
			property['_structLength'] = structSize
			for i in range(0, count):
				props = []
				#TODO: Add checkers
				#while (readProperty(props)):
				#	pass
				while (True):
					t = readProperty(props)
					if not t or not t[0]:
						break
					if not t[1]:
						print("  at property {}[{}]".format(property['type'],i))
						overallCheckState = False
				if not overallCheckState:
					print("  in ArrayProperty[{}].StructProperty, structName='{}', structType='{}'".format(len(values),structName,structType))

				values.append({
					'properties': props
				})

		elif itemType == 'IntProperty':
			for i in range(0, count):
				values.append(readInt())

		elif itemType == 'ByteProperty':
			for i in range(0, count):
				values.append(readByte())

		else:
			assertFail('unknown itemType ' + itemType + ' in name ' + name)

		property['value'] = {
			'type': itemType,
			'values': values
		}
		
	elif prop == 'ObjectProperty':
		assertNullByte()
		property['value'] = {
			'levelName': readLengthPrefixedString(),
			'pathName': readLengthPrefixedString()
		}
		
	elif prop == 'BoolProperty':
		property['value'] = readByte()
		assertNullByte()
		
	elif prop == 'FloatProperty':  # TimeStamps that are FloatProperties are negative to the current time in seconds?
		assertNullByte()
		property['value'] = readFloat()
		
	elif prop == 'EnumProperty':
		enumName = readLengthPrefixedString()
		assertNullByte()
		valueName = readLengthPrefixedString()
		property['value'] = {
			'enum': enumName,
			'value': valueName,
		}
		
	elif prop == 'NameProperty':
		assertNullByte()
		property['value'] = readLengthPrefixedString()
		
	elif prop == 'MapProperty':
		name = readLengthPrefixedString()
		valueType = readLengthPrefixedString()
		for i in range(0, 5):
			assertNullByte()
		count = readInt()
		values = {
		}
		for i in range(0, count):
			key = readInt()
			props = []
			#TODO: Add checkers
			#while readProperty(props):
			#	pass
			while (True):
				t = readProperty(props)
				if not t or not t[0]:
					break
				if not t[1]:
					print("  in MapProperty[{}], property '{}'".format(len(props),property['name']))
					overallCheckState = False
			values[key] = props

		property['value'] = {
			'name': name,
			'type': valueType,
			'values': values
		}
		
	elif prop == 'ByteProperty':  # TODO

		unk1 = readLengthPrefixedString()  # TODO
		if unk1 == 'None':
			assertNullByte()
			property['value'] = {
				'unk1': unk1,
				'unk2': readByte()
			}
		else:
			assertNullByte()
			unk2 = readLengthPrefixedString()  # TODO
			property['value'] = {
				'unk1': unk1,
				'unk2': unk2
			}
		
	elif prop == 'TextProperty':
		assertNullByte()
		property['textUnknown'] = readHex(13)  # TODO
		property['value'] = readLengthPrefixedString()
		
	else:
		assertFail('Unknown property type: ' + prop)

	properties.append(property)
	return True,overallCheckState


def readEntity(withNames, length):
	global bytesRead
	bytesRead = 0

	entity = {}

	if withNames:
		entity['levelName'] = readLengthPrefixedString()
		entity['pathName'] = readLengthPrefixedString()
		entity['children'] = []

		childCount = readInt()
		if childCount > 0:
			for i in range(0, childCount):
				levelName = readLengthPrefixedString()
				pathName = readLengthPrefixedString()
				entity['children'].append({
					'levelName': levelName,
					'pathName': pathName
				})
	entity['properties'] = []
	#TODO: Add checkers
	#while (readProperty(entity['properties'])):
	#	pass
	overallCheckState = True
	while (True):
		t = readProperty(entity['properties'])
		if not t or not t[0]:
			break
		if not t[1]:
			print("  at property '{}'".format(t[0]['name']))			
			overallCheckState = False
	if not overallCheckState:
		if withNames:
			print("  in entity '{}'".format(entity['pathName']))			
		else:
			print("  in entity")

	# read missing bytes at the end of this entity.
	# maybe we missed something while parsing the properties?
	missing = length - bytesRead
	if missing > 0:
		entity['missing'] = readHex(missing)
	elif missing < 0:
		assertFail('negative missing amount: ' + str(missing))

	return entity


for i in range(0, elementCount):
	length = readInt()  # length of this entry
	if hierarchy['objects'][i]['type'] == 1:
		hierarchy['objects'][i]['entity'] = readEntity(True, length)
	else:
		hierarchy['objects'][i]['entity'] = readEntity(False, length)


collectedCount = readInt()

for i in range(0, collectedCount):
	levelName = readLengthPrefixedString()
	pathName = readLengthPrefixedString()
	hierarchy['collected'].append({'levelName': levelName, 'pathName': pathName})

# store the remaining bytes as well so that we can recreate the exact same save file
hierarchy['missing'] = readHex(fileSize - f.tell())


print("\nInspected a total of {} objects.".format(elementCount+collectedCount))
if len(errors):
	print("A total of {} errors were found!".format(len(errors)))
else:
	print("NO errors found at all.")
