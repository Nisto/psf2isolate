import os
import sys
import zlib
import tempfile

MAX_BLOCK_SIZE = 32768
MAX_NAME_LEN = 36
VFS_ENT_SIZE = 48

DEFAULT_COMPRESSION_LEVEL = 9

ADPCM_BLOCK_SIZE = 16

SILENT_MIDBLOCK = b"\x0C\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
SILENT_ENDBLOCK = b"\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

def silence_sample(buf, ofs, size):
  start = ofs + ADPCM_BLOCK_SIZE # don't touch first block; should be all zero
  end = ofs + size - ADPCM_BLOCK_SIZE
  middle_size = end - start
  if middle_size >= ADPCM_BLOCK_SIZE:
    num_blocks = middle_size // ADPCM_BLOCK_SIZE
    buf[start:end] = SILENT_MIDBLOCK * num_blocks
  buf[end:end+ADPCM_BLOCK_SIZE] = SILENT_ENDBLOCK

def get_u32_le(b, off=0):
  return int.from_bytes(b[off:off+4], "little", signed=False)

def make_u32_le(n):
  return n.to_bytes(4, "little", signed=False)

def buildfile(reserved_buffer, filename, zlevel=DEFAULT_COMPRESSION_LEVEL):
  #print("[%d] file: %s" % (len(reserved_buffer), filename))

  length = os.path.getsize(filename)
  blocks = (length + (MAX_BLOCK_SIZE - 1)) // MAX_BLOCK_SIZE
  size_table = b""
  zlib_buffer = b""

  with open(filename, "rb") as f:
    for b in range(blocks):
      block_size = min(length-f.tell(), MAX_BLOCK_SIZE)
      block_buffer = f.read(block_size)
      if len(block_buffer) != block_size:
        print("error reading position %d" % f.tell())
        return -1

      block_zbuffer = zlib.compress(block_buffer, level=zlevel)
      if not block_zbuffer:
        print("error compressing position %d" % f.tell())
        return -1

      size_table += make_u32_le(len(block_zbuffer))
      zlib_buffer += block_zbuffer

  reserved_buffer += size_table
  reserved_buffer += zlib_buffer

  return 0

def builddir(reserved_buffer, dirname, zlevel=DEFAULT_COMPRESSION_LEVEL):
  #print("[%d] entering %s..." % (len(reserved_buffer), dirname))

  lastpath = os.getcwd()

  if not lastpath:
    print("unable to save previous dir; giving up")
    return -1

  if not os.chdir(dirname) is None:
    print("unable to switch to directory; giving up")
    return -1

  dirents = os.listdir(".")

  # write dirent count
  reserved_buffer += make_u32_le(len(dirents))

  # get offset for first entry
  ent_ofs = len(reserved_buffer)

  # reserve space for directory listing (VFS dirents must be in direct succession, i.e. no file data interleaved)
  reserved_buffer += b"\0" * VFS_ENT_SIZE * len(dirents)

  # process files and traverse subdirectories
  for ename in dirents:
    if len(ename) > MAX_NAME_LEN:
      print("filename '%s' is too long" % ename)
      return -1

    isdir = os.path.isdir(ename)

    # First 36 bytes: Filename (NOTE: zero-PADDED, NOT zero-TERMINATED)
    N = ename.encode("ascii", "ignore").ljust(MAX_NAME_LEN, b"\0")
    # Next 4 bytes: Offset (O) of the file data or subdirectory
    O = len(reserved_buffer)
    # Next 4 bytes: Uncompressed size (U)
    U = 0 if isdir else os.path.getsize(ename)
    # Next 4 bytes: Block size (B)
    B = 0 if isdir else MAX_BLOCK_SIZE

    entry = N + make_u32_le(O) + make_u32_le(U) + make_u32_le(B)
    reserved_buffer[ent_ofs:ent_ofs+len(entry)] = entry

    if isdir:
      if builddir(reserved_buffer, ename, zlevel) < 0:
        return -1
    elif os.path.getsize(ename):
      if buildfile(reserved_buffer, ename, zlevel) < 0:
        return -1

    ent_ofs += len(entry)

  if not os.chdir(lastpath) is None:
    print("unable to switch to previous directory; giving up")
    return -1

  #print("[%d] exiting %s (%d %s)" % (len(reserved_buffer), dirname, len(dirents), "entry" if len(dirents)==1 else "entries"))
  return 0

def psf2create(psf2filename, dirname, tags={}, zlevel=DEFAULT_COMPRESSION_LEVEL):
  if os.path.isfile(psf2filename):
    with open(psf2filename, "rb") as f:
      magic = f.read(4)
      if len(magic) != 4:
        print("can't verify whether %s is overwritable; quitting" % psf2filename)
        return -1
      if magic != b"PSF\x02":
        print("%s exists and is not PSF2; will not overwrite" % psf2filename)
        return -1

  reserved_buffer = bytearray()

  if builddir(reserved_buffer, dirname, zlevel) < 0:
    return -1

  #print("[%d] finished" % len(reserved_buffer))
  #print("creating %s..." % psf2filename)

  with open(psf2filename, "wb") as f:
    f.write(b"PSF\x02" + make_u32_le(len(reserved_buffer)) + b"\0"*8)
    f.write(reserved_buffer)
    if tags:
      tags["utf8"] = "1"
      taglines = [("%s=%s" % (name, tags[name])) for name in tags]
      f.write(("[TAG]" + "\n".join(taglines)).encode("utf-8"))

  #print("done")
  return 0

def psf2_print_vfs_files(psf2directory):
  paths = []

  for dirpath, dirnames, filenames in os.walk(psf2directory):
    for filename in filenames:
      path = os.path.join(dirpath, filename)
      relpath = os.path.relpath(path, psf2directory)
      paths.append(relpath)

  paths.sort(key=str.casefold)

  for path in paths[:7]:
    print("  %s" % path)
  if len(paths) > 14:
    print("  < +%d more files >" % (len(paths)-14))
  for path in paths[-7:]:
    print("  %s" % path)

def psf2_vfs_extract(base_path, reserved_data, ofs=0):
  n_entries = get_u32_le(reserved_data, ofs)

  ofs += 4

  for _ in range(n_entries):
    entry = reserved_data[ofs : ofs + VFS_ENT_SIZE]

    # First 36 bytes: Filename
    N = entry[:36].rstrip(b"\0").decode("ascii")
    # Next 4 bytes: Offset (O) of the file data or subdirectory 
    O = get_u32_le(entry, 36)
    # Next 4 bytes: Uncompressed size (U) 
    U = get_u32_le(entry, 40)
    # Next 4 bytes: Block size (B)
    B = get_u32_le(entry, 44)

    path = os.path.join(base_path, N)

    # If U, B, and O are all zero, then the entry describes a zero-length file. In this case, there is no data.
    if U == 0 and B == 0 and O == 0:
      os.touch(path)
    # If U and B are zero and O is nonzero, the entry describes a subdirectory.
    elif U == 0 and B == 0 and O != 0:
      os.makedirs(path, exist_ok=True)
      psf2_vfs_extract(path, reserved_data, O)
    # Otherwise, the entry describes a regular file.
    else:
      num_blocks = (U + B - 1) // B
      size_table = reserved_data[O : O + 4*num_blocks]
      subofs = O + len(size_table)
      with open(path, "wb") as out:
        for b in range(num_blocks):
          compressed_blocksize = get_u32_le(size_table, b*4)
          compressed_block = reserved_data[subofs : subofs + compressed_blocksize]
          decompressed_block = zlib.decompress(compressed_block)
          out.write(decompressed_block)
          subofs += len(compressed_block)

    ofs += len(entry)

def psf2load(psf2_path, out_root, tags={}, islib=False):
  with open(psf2_path, "rb") as f:
    data = f.read()

  if data[:4] != b"PSF\x02":
    raise Exception("Not a PSF2 file")

  reserved_size = get_u32_le(data, 0x04)

  tag_data = data[0x10+reserved_size:]

  reserved_data = data[0x10:0x10+reserved_size]

  # "" First, recursively load the virtual filesystems from each PSF2 file named by a library tag. ""

  if islib:
    psf2_vfs_extract(out_root, reserved_data)

  if tag_data[:5] == b"[TAG]":
    # Read *all* raw tags
    tag_lines = tag_data[5:].strip().decode("utf-8").split("\n")
    for tag_line in tag_lines:
      tag_name, tag_val = tag_line.split("=", 1)
      # this can probably be more faithful to spec
      # (should be same order as VFS loading order, I think??)
      # but eh.........
      if not islib or tag_name not in tags:
        tags[tag_name] = tag_val

    # Separate valid _lib tags into a path array (we don't want to send these further..)
    lib_paths = []
    libn = 1
    while True:
      lib_tagname = "_lib" if libn == 1 else ("_lib%d" % libn)
      if lib_tagname in tags:
        lib_paths.append(tags[lib_tagname])
        del tags[lib_tagname]
        libn += 1
      else:
        break

    # Load _lib files
    for lib_path in lib_paths:
      psf2_dirpath = os.path.dirname(psf2_path)
      psf2lib_name = lib_path.replace("\\", os.sep).replace("/", os.sep)
      psf2lib_path = os.path.join(psf2_dirpath, psf2lib_name)
      psf2load(psf2lib_path, out_root, tags, islib=True)

  # "" Then, load the virtual filesystem from the current PSF2 file. ""

  if not islib:
    psf2_vfs_extract(out_root, reserved_data)

  return tags

def get_module_arguments(ini_path):
  module_arguments = []

  with open(ini_path, "r") as f:
    for line in f.readlines():
      args = line.split(" ")
      if len(args) > 1:
        for arg in args[1:]:
          sarg = arg.strip()
          if sarg:
            module_arguments.append(sarg)

  return module_arguments

def rootname(x):
  if os.path.isdir(x):
    return os.path.basename(x)
  return os.path.splitext(os.path.basename(x))[0]

def number_in_str(haystack, needle):
  uhaystack = haystack.upper()

  try:
    n = int(needle, 0)
  except ValueError:
    return False

  if ("%X" % n) in uhaystack: return True
  if ("%d" % n) in uhaystack: return True

  return False

def find_best_strmatch(haystacks, needles):
  for needle in needles:
    uneedle = needle.upper()
    for haystack in haystacks:
      uhaystack = haystack.upper()
      if uneedle in uhaystack \
      or number_in_str(uhaystack, needle):
        return haystack

def ask_filename(label, default=None, root="."):
  while True:
    if default is not None:
      input_name = input("  %s [default: %s]: " % (label, default))
    else:
      input_name = input("  %s: " % (label, default))

    input_name = input_name.strip().strip('"')

    if not input_name.strip():
      input_name = default

    path = os.path.join(root, input_name)

    if os.path.isfile(path):
      return path

def select_soundbank(psf2name, psf2directory):
  hd_name = None
  bd_name = None

  hd_files = []
  bd_files = []

  for dirpath, dirnames, filenames in os.walk(psf2directory):
    for filename in filenames:
      filepath = os.path.join(dirpath, filename)
      relpath = os.path.relpath(filepath, psf2directory)
      with open(filepath, "rb") as f:
        magic = f.read(8)
      if magic == b"IECSsreV":
        hd_files.append(relpath)
      elif os.path.splitext(filename)[1].upper() == ".BD":
        bd_files.append(relpath)

  if len(hd_files) > 1 \
  or len(bd_files) > 1 :
    search_words = [psf2name] # prio #1: PSF2 name
    ini_path = os.path.join(psf2directory, "psf2.ini")
    module_arguments = get_module_arguments(ini_path)
    search_words.extend(module_arguments) # prio #2: module arguments

  # Guess .HD name
  if len(hd_files) == 1:
    hd_name = hd_files[0]
  elif len(hd_files) > 1:
    hd_name = find_best_strmatch(hd_files, search_words)

  # Guess .BD name
  if len(bd_files) == 1:
    bd_name = bd_files[0]
  elif len(bd_files) > 1:
    if hd_name: search_words.insert(0, rootname(hd_name)) # prio #0: .HD rootname
    bd_name = find_best_strmatch(bd_files, search_words)

  if len(hd_files) == 0:
    print("* No HD/BD soundbanks detected - exiting.")
  elif len(hd_files) == 1 and len(bd_files) == 1:
    print("* Single HD/BD soundbank detected:")
    print("  HD: %s" % hd_name)
    print("  BD: %s" % bd_name)
    hd_name = os.path.join(psf2directory, hd_name)
    bd_name = os.path.join(psf2directory, bd_name)
  elif len(hd_files) > 1 and len(bd_files) > 1:
    print("* Multiple HD/BD soundbank files detected - confirm names:")
    hd_name = ask_filename("HD", hd_name, psf2directory)
    bd_name = ask_filename("BD", bd_name, psf2directory)
  else:
    print("* Supply HD/BD soundbank filenames:")
    hd_name = ask_filename("HD", hd_name, psf2directory)
    bd_name = ask_filename("BD", bd_name, psf2directory)

  return hd_name, bd_name

def get_sample_offsets(hd_path):
  with open(hd_path, "rb") as f:
    data = f.read()

  sample_offsets = []

  head_ofs = get_u32_le(data, 0x08)
  vagi_ofs = get_u32_le(data, head_ofs+0x20)
  max_vagi_num = get_u32_le(data, vagi_ofs+0x0C)
  for n in range(max_vagi_num+1):
    param_ofs = get_u32_le(data, vagi_ofs+0x10+n*4)
    sample_ofs = get_u32_le(data, vagi_ofs+param_ofs+0x00)
    sample_offsets.append(sample_ofs)

  sample_offsets.sort()

  return sample_offsets

def main(argc=len(sys.argv), argv=sys.argv):
  if argc != 2:
    print("Usage: %s <psf2>" % argv[0])
    return 1

  psf2filename = os.path.abspath(argv[1])

  if not os.path.isfile(psf2filename):
    print("Invalid PSF2 path")
    return 1

  psf2_rootname = rootname(psf2filename)
  psf2_out_root = os.path.dirname(psf2filename)

  # Extract input PSF2 and create PSF2LIB
  with tempfile.TemporaryDirectory() as psf2directory:
    print("* Loading PSF2...")
    psf2tags = psf2load(psf2filename, psf2directory)
    print()

    print("* Loaded PSF2 virtual filesystem:")
    psf2_print_vfs_files(psf2directory)
    print()

    # Determine HD/BD paths and names
    hd_filename, bd_filename = select_soundbank(psf2_rootname, psf2directory)
    print()
    if hd_filename is None or bd_filename is None:
      input("Press enter to exit")
      return 1
    bd_vfs_path = os.path.relpath(bd_filename, psf2directory)

    # Read BD data
    with open(bd_filename, "rb") as f:
      bd_data = f.read()

    # Remove original .BD file (new .BD file is written for each isolated sample)
    os.remove(os.path.join(psf2directory, bd_filename))

    # Get sample offsets/sizes
    sample_offsets = get_sample_offsets(hd_filename)
    sample_sizes = []

    # Create silent .BD buffer
    silent_bd_data = bytearray(bd_data[:])
    for i, sample_offset in enumerate(sample_offsets):
      if i+1 < len(sample_offsets):
        sample_size = sample_offsets[i+1] - sample_offset
      else:
        sample_size = len(bd_data) - sample_offset
      sample_sizes.append(sample_size)
      silence_sample(silent_bd_data, sample_offset, sample_size)

    # Create PSF2LIB from current VFS files (no .BD)
    psf2lib_name = "%s_silent.psf2lib" % psf2_rootname
    psf2lib_path = os.path.join(psf2_out_root, psf2lib_name)
    print("* Writing psf2lib to: %s ..." % psf2lib_path)
    psf2create(psf2lib_path, psf2directory)

    # Indicate .psf2lib name for .minipsf2s
    psf2tags["_lib"] = psf2lib_name

  # Create a miniPSF2 (.BD file only) for each sample isolated
  with tempfile.TemporaryDirectory() as psf2directory:
    temp_sample_bd_path = os.path.join(psf2directory, bd_vfs_path)
    temp_sample_bd_dir = os.path.dirname(temp_sample_bd_path)

    if not os.path.isdir(temp_sample_bd_dir):
      os.makedirs(temp_sample_bd_dir)

    with open(temp_sample_bd_path, "wb") as f:
      # Start by writing full .BD with silent samples
      f.write(silent_bd_data)

      for i, sample_offset in enumerate(sample_offsets):
        # Overwrite silent sample data with real sample data
        f.seek(sample_offset)
        f.write(bd_data[sample_offset:sample_offset+sample_sizes[i]])
        f.flush()

        # Create miniPSF2
        minipsf2_name = "%s_sample_%d.minipsf2" % (psf2_rootname, i)
        minipsf2_path = os.path.join(psf2_out_root, minipsf2_name)
        print("* Writing minipsf2 for isolated sample %d to: %s ..." % (i, minipsf2_path))
        psf2create(minipsf2_path, psf2directory, psf2tags)

        # Overwrite real sample data with silent sample data again
        f.seek(sample_offset)
        f.write(silent_bd_data[sample_offset:sample_offset+sample_sizes[i]])
        f.flush()

  input("\nDone! Press Enter to exit")

  return 0

if __name__ == "__main__":

  main()

