#!/usr/bin/python3
import sys
import os.path
import struct

IDENT = "IDP3"
VERSION = 15
f = ""

def printUsage():
	print("USAGE: %s in-md3 [ out-md3 shader-number new-shader ]" % sys.argv[0])

def validateArgs():
	if len(sys.argv) == 1:
		printUsage()
		sys.exit(0)

	if len(sys.argv) > 1 and not os.path.isfile(sys.argv[1]):
		print("ERROR: %s does not exist." % sys.argv[1])
		sys.exit(0)

	if len(sys.argv) > 2:
		if len(sys.argv) != 5:
			print("Incorrect number of arguments")
			printUsage()
			sys.exit(0)

def readint():
	return int.from_bytes(f.read(4), "little")

def readchar():
	return int.from_bytes(f.read(1), "little")

def readstring(length):
	s = f.read(length)
	string = str(s, encoding='ascii')
	return string[:string.find('\0')]

def readfloat():
	return struct.unpack('f', f.read(4))[0]

def readshort():
	return struct.unpack('h', f.read(2))[0]

def readvec():
	return [ readfloat(), readfloat(), readfloat() ]

def readframe():
	return {
		"min": readvec(),
		"max": readvec(),
		"origin": readvec(),
		"radius": readfloat(),
		"name": readstring(16)
	};

def readtag():
	return {
		"name": readstring(64),
		"origin": readvec(),
		"radius": readvec(),
		"axis": [
			readvec(),
			readvec(),
			readvec()
		]
	};

def readshader():
	return {
		"name": readstring(64),
		"shader_index": readint()
	};

def readtriangle():
	return [ readint(), readint(), readint() ]

def readst():
	return [ readfloat(), readfloat() ]

def readvertex():
	return [ readshort(), readshort(), readshort(), readshort() ]

def readsurface():
	# Record start of surface
	surface_start = f.tell()

	# Read in
	surface =  {
		"ident": readint(),
		"name": readstring(64),
		"flags": readint(),
		"num_frames": readint(),
		"num_shaders": readint(),
		"num_verts": readint(),
		"num_triangles": readint(),
		"ofs_triangles": readint(),
		"ofs_shaders": readint(),
		"ofs_st": readint(),
		"ofs_xyznormal": readint(),
		"ofs_end": readint()
	};

	# Read shaders
	f.seek(surface_start + surface['ofs_shaders'])
	surface['shaders'] = []
	for i in range(0, surface['num_shaders']):
		surface['shaders'].append(readshader())

	# Read Triangles
	f.seek(surface_start + surface['ofs_triangles'])
	surface['triangles'] = []
	for i in range(0, surface['num_triangles']):
		surface['triangles'].append(readtriangle())

	# Read texture coords
	f.seek(surface_start + surface['ofs_st'])
	surface['st'] = []
	for i in range(0, surface['num_verts']):
		surface['st'].append(readst())

	# Read XYZNormals
	f.seek(surface_start + surface['ofs_xyznormal'])
	surface['xyznormal'] = []
	for i in range(0, surface['num_frames'] * surface['num_verts']):
		surface['xyznormal'].append(readvertex())

	# Reset file position so next surface can be read
	f.seek(surface_start + surface['ofs_end'])

	return surface

def writestring(s, length):
	return bytes(s.ljust(length, '\0'), encoding="ascii")

def writemd3(md3):
	size_frame = 12+12+12+4+16
	size_tag = 64 + 12 + 36
	size_vert = 8
	size_st = 8
	size_tri = 12
	size_shader = 68
	size_surfaces = 0
	size_md3_frames = size_frame * md3['num_frames']
	size_tags = size_tag * md3['num_tags']

	surfaces = bytearray()
	for surface in md3['surfaces']:
		size_shaders = size_shader * surface['num_shaders']
		size_tris = size_tri * surface['num_triangles']
		size_frames = size_frame * surface['num_frames']
		size_sts = size_st * surface['num_verts']
		size_verts = size_vert * len(surface['xyznormal'])

		surfaces += struct.pack('i', surface['ident'])
		surfaces += writestring(surface['name'], 64)
		surfaces += struct.pack('i', surface['flags'])
		surfaces += struct.pack('i', surface['num_frames'])
		surfaces += struct.pack('i', surface['num_shaders'])
		surfaces += struct.pack('i', surface['num_verts'])
		surfaces += struct.pack('i', surface['num_triangles'])
		surfaces += struct.pack('i', 108 + size_shaders)
		surfaces += struct.pack('i', 108)
		surfaces += struct.pack('i', 108 + size_tris + size_shaders)
		surfaces += struct.pack('i', 108 + size_tris + size_shaders + size_sts)
		surfaces += struct.pack('i', 108 + size_tris + size_shaders + size_sts + size_verts)
		size_surfaces += 108 + size_tris + size_shaders + size_sts + size_verts
		for shader in surface['shaders']:
			surfaces += writestring(shader['name'], 64)
			surfaces += struct.pack('i', shader['shader_index'])

		for tri in surface['triangles']:
			surfaces += struct.pack('iii', tri[0], tri[1], tri[2])

		for st  in surface['st']:
			surfaces += struct.pack('ff', st[0], st[1])

		for vert in surface['xyznormal']:
			surfaces += struct.pack('hhhh', vert[0], vert[1], vert[2], vert[3])

	tags = bytearray()
	for tag in md3['tags']:
		tags += writestring(tag['name'], 64)
		tags += struct.pack('fff', tag['origin'][0], tag['origin'][1], tag['origin'][2])
		tags += struct.pack('fffffffff', tag['axis'][0][0], tag['axis'][0][1], tag['axis'][0][2],
					  tag['axis'][1][0], tag['axis'][1][1], tag['axis'][1][2],
					  tag['axis'][2][0], tag['axis'][2][1], tag['axis'][2][2]
					  )

	frames = bytearray()
	for frame in md3['frames']:
		frames += struct.pack('fff', frame['min'][0], frame['min'][1], frame['min'][2])
		frames += struct.pack('fff', frame['max'][0], frame['max'][1], frame['max'][2])
		frames += struct.pack('fff', frame['origin'][0], frame['origin'][1], frame['origin'][2])
		frames += struct.pack('f', frame['radius'])
		frames += writestring(frame['name'], 16)

	raw = bytearray()
	raw += struct.pack('i', md3['ident'])
	raw += struct.pack('i', md3['version'])
	raw += writestring(md3['name'], 64)
	raw += struct.pack('i', md3['flags'])
	raw += struct.pack('i', md3['num_frames'])
	raw += struct.pack('i', md3['num_tags'])
	raw += struct.pack('i', md3['num_surfaces'])
	raw += struct.pack('i', md3['num_skins'])
	raw += struct.pack('i', 108)
	raw += struct.pack('i', 108 + size_md3_frames)
	raw += struct.pack('i', 108 + size_md3_frames + size_tags)
	raw += struct.pack('i', 108 + size_md3_frames + size_tags + size_surfaces)
	raw += frames
	raw += tags
	raw += surfaces

	open(sys.argv[2], "wb").write(raw)

def main():
	global f
	validateArgs()
	f = open(sys.argv[1], "rb")

	md3 = dict()

	# Read Header
	md3['ident'] = readint()
	md3['version'] = readint()
	md3['name'] = readstring(64)
	md3['flags'] = readint()
	md3['num_frames'] = readint()
	md3['num_tags'] = readint()
	md3['num_surfaces'] = readint()
	md3['num_skins'] = readint()
	md3['ofs_frames'] = readint()
	md3['ofs_tags'] = readint()
	md3['ofs_surfaces'] = readint()
	md3['ofs_eof'] = readint()

	# Read Frames
	f.seek(md3['ofs_frames'])
	md3['frames'] = []
	for i in range(0, md3['num_frames']):
		md3['frames'].append(readframe())

	# Read Tags
	f.seek(md3['ofs_tags'])
	md3['tags'] = []
	for i in range(0, md3['num_tags']):
		md3['tags'].append(readtag())

	# Read surfaces
	f.seek(md3['ofs_surfaces'])
	md3['surfaces'] = []
	for i in range(0, md3['num_surfaces']):
		md3['surfaces'].append(readsurface())

	# Done
	f.close()

	if len(sys.argv) == 2:
		shader_num = 0
		for surface in md3['surfaces']:
			for shader in surface['shaders']:
				shader_num += 1
				print("%d: %s" % (shader_num, shader['name']))
		sys.exit(0)

	shader_num = 0
	for surface in md3['surfaces']:
		for shader in surface['shaders']:
			shader_num += 1
			if shader_num == int(sys.argv[3]):
				print("Modifying shader... %s => %s" % (shader['name'], sys.argv[4]))
				shader['name'] = sys.argv[4]

	writemd3(md3)

main()
