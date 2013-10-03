import uuid
import json
import time
import libvirt
import random
import col
import sys
import os
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, url_for,g, _app_ctx_stack,jsonify,flash,abort

# XML construction - (name, uuid, memory, vcpu, source file, mac (last 3 octets))

DATABASE = './sqlite.db'
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('DB_SETTINGS', silent=True)

def get_db():
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db


@app.teardown_appcontext
def close_database(exception):
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


def query_db(query, args=(), one=False):
        cur = get_db().execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv

def init_db():
        with app.app_context():
		print sys.argv
                db = get_db()
                with app.open_resource('../src/schema.sql', mode='r') as f:
                        db.cursor().executescript(f.read())
		db.commit()

                VMTypes=json.loads(open(sys.argv[3],'r').read());

                Machines=open(sys.argv[1],'r').read().split('\n');

                Images=open(sys.argv[2],'r').read().split('\n');

                for Type in VMTypes['types']:
                        db.execute('''insert into vmTypes (tid,cpu,ram,disk) values (?,?,?,?)''',(Type['tid'],Type['cpu'],Type['ram'],Type['disk']))
                        db.commit()
                for Image in Images:
                        if Image:
				print Image
                                db.execute('''insert into images (path) values (?)''',[str(Image.strip('\n\r'))])
                                db.commit()

                for Machine in Machines:
                        if Machine:
                                path=str(Machine.strip('\n\r'));
                                cpu=int(os.popen('ssh '+str(Machine)+' "grep processor /proc/cpuinfo | wc -l"').read().split('\n')[0]);
#                                cpu=int(os.popen('ssh '+Machine+' "lscpu | head -4 | tail -1"').read().split('\n')[0].split()[1]);
                                ram=(reduce( lambda x,y:x+y,[int(i.split()[1]) for i in os.popen('ssh '+str(Machine)+' "cat /proc/meminfo | head -4 | tail -3"').read().split('\n') if i] )/1024)
                                disk=0 # for now no need for diskcheck
                                image_count=0
                                arch=os.popen('ssh '+str(Machine)+' "getconf LONG_BIT"').read().split('\n')[0]
                                db.execute('''insert into machines (path,cpu,ram,disk,image_count,arch) values (?,?,?,?,?,?)''',(path,cpu,ram,disk,image_count,arch))
                                db.commit()




def selectMachine(instance_type,image_id):
	instance_type=query_db('select * from vmTypes where tid=?',[instance_type]);
	machineID=0
	path=""
	if instance_type:
		instance_type=instance_type[0]
		cpu=instance_type[1]
		ram=instance_type[2]
		disk=instance_type[3]
		imageDetails=query_db('select * from images where iid=?',[image_id]);
		if imageDetails:
			imageDetails=imageDetails[0]
			imageName='.'.join(imageDetails[1].split('/')[-1].split('.')[0:-1])
			print imageName
			print instance_type
			machine=query_db('select * from machines');
			for i in machine:
				print i
				if i[3]>=ram and i[2]>=cpu:
					print i[6]
					if ( int(i[6])==32 and imageName[-3:]!='_64') or ( int(i[6])==64 ) :
						machineID=i[0]
						path=i[1]
						print i[0],i[1]
						return [machineID,path,i[3]-ram,i[2]-cpu,i[6]]
	return [machineID,path]	
	


# create?name=test_vm&instance_type=type&image_id=id
@app.route("/vm/create")
def createVM():
	instance_type=int(request.args.get('instance_type'));
	image_id=int(request.args.get('image_id'))
	machineDetails=selectMachine(instance_type,image_id)
	if len(machineDetails)==5:
		name=request.args.get('name')
		imageDetails=query_db('select * from images where iid=?',[image_id], one=True);
		imageName=str('.'.join(imageDetails[1].split('/')[-1].split('.')[0:-1]).strip('\n\r'));
		imageExt=str(imageDetails[1].split('/')[-1].split('.')[-1].strip('\n\r'))
		clientCount=query_db('select count(*) from clients')[0][0];
		clientCount=clientCount+1;
		print clientCount
		instance_type=query_db('select * from vmTypes where tid=?',[instance_type]);
		instance_type=instance_type[0]
		cpu=instance_type[1]
		ram=instance_type[2]
		disk=instance_type[3]
		#copy image from imageDetails[1] to machiceDetails[1] with name clientCount append clientCount at the end of all for uniqueness
		print imageDetails[1]
		print machineDetails[1]
		print imageName+str(clientCount)+'.'+imageExt
		imagePath=str("/")+str(imageName)+str(clientCount)+str(".")+str(imageExt)
		print imagePath
		print "-----------------"
		cmd=str("scp ")+str(imageDetails[1].strip('\n\r'))+str(" ")+str(machineDetails[1])+str(":/")+str(imageName)+str(clientCount)+str(".")+str(imageExt)
		print cmd
		print type(cmd)
		imageCopy=os.popen(cmd).read()
		print machineDetails[1]
		print "-----------------"
		print imageCopy
		#create vm if no error else retun 0
		vmid = col.createVM(imagePath,name,ram,cpu,machineDetails[4],machineDetails[1])
		print vmid
		if vmid!=-1:
       	        	db = get_db()
			print name,image_id
                	db.execute('''insert into clients (vmid,name,vtid,mid) values (?,?,?,?)''',[int(vmid),str(name),int(instance_type[0]),int(machineDetails[0])])
			db.commit()
			db.execute('''update machines set ram=?,cpu=? where mid=?''',[machineDetails[2],machineDetails[3],machineDetails[0]]);
			db.commit()
			cid=query_db('select cid from clients')[-1];
			vmInfo = {'vmid':cid[0]}
			return jsonify(vmInfo)
		else:
			print 'error'
			vmInfo = {'vmid': 0}
			return jsonify(vmInfo)
	else:
		print 'error'
		vmInfo = {'vmid': 0}
		return jsonify(vmInfo)

@app.route("/vm/query")
def queryVM():	
	vmid = int(request.args.get('vmid'))
	clientDetails=query_db('select * from clients where cid=?',[vmid], one=True);
	if clientDetails:
		return jsonify({'vmid':vmid,'name':clientDetails[2],'instance_type':clientDetails[3],'pmid':clientDetails[4]})
	else:
		return jsonify({'vmid':0,'name':None,'instance_type':0,'pmid':0})

@app.route("/vm/destroy")
def destroyVM():
	vmid = int(request.args.get('vmid'))
	clientDetails=query_db('select * from clients where cid=?',[vmid]);
	if clientDetails:
		clientDetails=clientDetails[0];
		machineDetails=query_db('select * from machines where mid=?',[clientDetails[4]], one=True);
		path=machineDetails[1]
		vmid=clientDetails[1]
		#destroy this vm at host path with this vmid
		retVal=col.destroyVM(path,vmid)
		if retVal!=-1: 
			instance_type=query_db('select * from vmTypes where tid=?',[clientDetails[3]], one=True);
        		cpu=instance_type[1]
        		ram=instance_type[2]
        		disk=instance_type[3]
       	        	db = get_db()
        		db.execute('''update machines set ram=?,cpu=? where mid=?''',[machineDetails[3]+ram,machineDetails[2]+cpu,machineDetails[0]]);
			db.commit()
       
			db.execute('''delete from clients where cid=?''',[clientDetails[0]]);
			db.commit()
			return jsonify({'status':1})
		else:
			return jsonify({'status':0})
	else:
		return jsonify({'status':0})


@app.route("/vm/types")
def listTypes():
    return jsonify(json.loads(open(sys.argv[3],'r').read()));

@app.route("/image/list")
def listImages():
	images=query_db('select * from images');
	imagesList={'images':[]}
	for i in images:
		imageName='.'.join(i[1].split('/')[-1].split('.')[0:-1])
		imagesList['images'].append({'id':i[0],'name':imageName})
	return jsonify(imagesList)


if __name__ == '__main__':
    app.debug = True
    init_db()
    app.run()
