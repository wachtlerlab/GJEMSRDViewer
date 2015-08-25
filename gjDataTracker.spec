# -*- mode: python -*-

block_cipher = None


a = Analysis(['GJEMSRDViewer.py'],
             pathex=['E:\GJEMSRawDataViewer'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='gjRawDataViewer',
          debug=False,
          strip=None,
          upx=True,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='gjRawDataViewer')
