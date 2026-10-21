from pathlib import Path
import hashlib, io, json, struct, zipfile
root=Path(__file__).resolve().parents[1]
apk=root/'app/build/outputs/apk/release/app-release.apk'
with zipfile.ZipFile(apk) as z:
    names=set(z.namelist())
    assert not any(n.endswith(('.p12','.jks','signing.properties')) for n in names)
    assets=root/'app/src/main/assets'
    count=0
    for p in assets.rglob('*'):
        if p.is_file():
            name='assets/'+p.relative_to(assets).as_posix()
            assert z.read(name)==p.read_bytes(),name
            count+=1
    modules=[]
    for n in names:
        if n.startswith('assets/chaquopy/') and n.endswith('.imy'):
            with zipfile.ZipFile(io.BytesIO(z.read(n))) as nested:
                modules+=nested.namelist()
    for module in ['mobile_server.py','model_provider.py','static_server.py','tts_server.py','edge_tts/__init__.py']:
        assert module in modules,module
    libs=[n for n in names if n.startswith('lib/') and n.endswith('.so')]
    for n in libs:
        data=z.read(n)
        assert data[:5]==b'\x7fELF\x02'
        phoff=struct.unpack_from('<Q',data,32)[0]
        phsize,phnum=struct.unpack_from('<HH',data,54)
        for i in range(phnum):
            ph=struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsize)
            if ph[0]==1:assert ph[7]>=16384,(n,ph[7])
print(json.dumps({'status':'PASS','bundled_asset_files':count,'native_libraries':len(libs),
    'native_page_alignment':'16 KiB or greater','python_source_modules':'present',
    'bytes':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest()}))
