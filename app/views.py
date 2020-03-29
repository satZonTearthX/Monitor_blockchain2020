from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from Monitor_blockchain2020.player import settings
from ftplib import FTP, parse227, parse229
import os
import time
import hashlib
import pymysql
import qrcode

import socket, json
from threading import Thread

IP = '47.92.76.75'
PORT = 9999
S_ADD = (IP, PORT)
real_hash=''
files_involved=[]
files_involved_result=[]
name_involved=[]
videos_involved=[]
user_name=''
# database config
DB_HOST = '39.100.228.145'
DB_ID = 'thepmc'
DB_PASSWORD = 'thepmc123'
DB_NAME = 'Video_information'
TABLE_NAME = 'Store_Information'
NAME_DICT = {701824309:'贵州幼儿园小班摄像头a',701824310:'贵州幼儿园小班摄像头b',701824311:'贵州幼儿园中班摄像头a',701824312:'贵州幼儿园中班摄像头b',701824313:'贵州幼儿园大班摄像头a',701824314:'贵州幼儿园大班摄像头b'}


class MyThread(Thread):
    def __init__(self, func, args):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception:
            return None


class Mysql_service(object):
    db = pymysql.connect(host=DB_HOST, user=DB_ID, password=DB_PASSWORD, db=DB_NAME)
    cursor = db.cursor()
    def __init__(self):
        print("connection on")

    def getHash(self,vName):

        try:
            sql = '''select * from %s where Video_Name='%s';''' % (TABLE_NAME, vName)
            # 执行sql语句
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            print(data)
            if data is None:
                Video_Hash = '-1'
            else:
                Video_Hash =data[5]
            print(Video_Hash)
        except Exception as e:
            # 如果发生错误则回滚
            print(e)
            self.db.rollback()

        return Video_Hash

    def getDownload(self,vName):
        downloadInfo=[]
        try:
            sql = '''select * from %s where Video_Name='%s';''' % (TABLE_NAME, vName)
            # 执行sql语句
            self.cursor.execute(sql)
            data = self.cursor.fetchone()
            print(data)
            if data is None:
                downloadInfo=[]
            else:
                for i in range(6,10):
                    downloadInfo.append(data[i])

            print(downloadInfo)
        except Exception as e:
            # 如果发生错误则回滚
            print(e)
            self.db.rollback()

        return downloadInfo

def task1(str1):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(S_ADD)#全局套接字
    msg=str1
    client.send(msg.encode('utf-8'))
    recv_data = client.recv(1024)
    real_hash = recv_data.decode('utf-8')
    client.close()
    return real_hash

def task_login(str1):
    files_involved=[]
    files_involved_str=''
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(S_ADD)#全局套接字
    msg=str1
    client.send(msg.encode('utf-8'))
    recv_data = client.recv(1024)
    files_involved_str = recv_data.decode('utf-8')
    if files_involved_str=='0':
        files_involved.clear()
    else:
        files_involved=files_involved_str.split('%')

    print(files_involved)


    client.close()
    return files_involved


def login(request):
    ftpIp = '39.100.228.145'
    ftpUser = 'thepmc'
    ftpPwd = 'thepmc123'
    global videos_involved
    global files_involved
    files_involved_result=[]
    if request.method == 'POST':
        sendfinal = '2%'

        print(sendfinal)
        data = json.loads(request.body)
        usr = data['username']
        psw = data['password']
        global user_name
        user_name=usr
        user = authenticate(username=usr, password=psw)
        msg = False

        if user is not None and user.is_active:
            auth_login(request, user)
            msg = True

            sendfinal = '2%'+usr
            print(usr)
            print('sendfinal'+sendfinal)#这是我传过去的最终内容
            t_login = MyThread(task_login, args=(sendfinal,))
            t_login.start()
            while t_login.get_result() is None:
                i = 0  # 手动锁等有值
            files_involved = t_login.get_result()
            #files_involved=['701824309', '701824310','701824314']#把以上注释取消，并且把本行赋值删除
            print('file_list=' + str(files_involved))

            if files_involved:
                ftp = MyFTP(ftpIp)
                ftp.set_debuglevel(2)
                ftp.login(ftpUser, ftpPwd)
                ftp.set_pasv(1)
                ftp.cwd('video')
                for i in files_involved:

                    ftpAdd=str(i)
                    ftp.cwd(ftpAdd)
                    print(ftp.nlst())
                    temlist=ftp.nlst()
                    for j in temlist:
                        files_involved_result.append(i)
                    videos_involved.extend(temlist)
                    ftp.cwd('..')
                print('video_involved='+str(videos_involved))
                # if str(os.getcwd()[-5:]) != 'media':
                #     print(os.getcwd())
                #     print('88888')
                os.chdir(settings.MEDIA_DIR)  # 进入视频总文件夹，以后要加密
                if not (os.path.exists(user_name)):
                    os.makedirs(user_name)
                    os.chdir('../..')          #新建用户目录建完回退
            else:
                msg=False

        return JsonResponse({'login': msg})
    return render(request, 'login.html')


@login_required
def logout(request):
    auth_logout(request)
    return redirect('/login')


@login_required
def index(request):
    global videos_involved
    global name_involved
    global NAME_DICT
    name_involved=[]
    for video in videos_involved:
       name_involved.append(NAME_DICT[int(video[12:21])])
    print('videos_involved'+str(videos_involved))

    return render(request, 'q_all.html', {'title': '视频查询', 'namelist':json.dumps(name_involved), 'videolist':json.dumps(videos_involved)})

@login_required
def query_all(request):
    global videos_involved
    global name_involved
    global NAME_DICT
    name_involved=[]
    for video in videos_involved:
       name_involved.append(NAME_DICT[int(video[12:21])])
    print('videos_involved'+str(videos_involved))

    return render(request, 'q_all.html', {'title': '视频查询', 'namelist':json.dumps(name_involved), 'videolist':json.dumps(videos_involved)})


@login_required
def personal_info(request):
    return render(request, 'my.html', {'title': '个人信息'})

@login_required
def log_info(request):
    return render(request, 'log.html', {'title': '日志记录'})



@login_required
def video_list(request):
    return render(request, 'list.html', {'title': '视频列表'})


def timestamp_to_datetime(timestamp):
    time_array = time.localtime(timestamp)
    return time.strftime("%Y-%m-%d %H:%M:%S", time_array)



@require_GET
@login_required
def get_video_list(request):
    global user_name
    print(os.getcwd())
    print(os.getcwd())
    filename_list = os.listdir(settings.MEDIA_DIR + '\\' + user_name)
    print(os.getcwd())
    print(filename_list)
    address_list=[]
    for i in filename_list:
        if not i.split(".")[-1] in ("mp4", "MP4"):
            filename_list.remove(i)
    print('filenamelist='+str(filename_list))
    for j in filename_list:
        address_list.append(NAME_DICT[int(j[12:21])])

    print(address_list)
    return JsonResponse([
        {
            'name': filename_list[z],
            'address':address_list[z],
            'created_at': timestamp_to_datetime(os.path.getmtime(os.path.join(settings.MEDIA_DIR + '\\' + user_name, filename_list[z]))),

        }
        for z in range(len(filename_list))



    ], safe=False)


@login_required
def play_video(request):
    global user_name
    filename = request.GET.get('filename')
    print(request.GET)
    ctime = timestamp_to_datetime(os.path.getmtime(os.path.join(settings.MEDIA_DIR + '\\' + user_name, filename)))
    url = '/media/'+ user_name+'/' + filename
    print('play '+filename)
    return render(request, "player.html",
                  {'title': '视频播放', 'video_name': filename, 'video_created_at': ctime, 'video_url': url})


@login_required
def hash_verity(request):
    filename = request.GET.get('filename')
    videoCreateTime = request.GET.get('videoCreateTime')
    print(filename)
    cameraId=filename[12:21]
    cameraName=NAME_DICT[int(cameraId)]
    videoShotTime=filename[:4]+"-"+filename[4:6]+"-"+filename[6:8]+" "+filename[8:10]+":"+filename[10:12]+":"+"00"
    verifyTime=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    Hash_tool="SHA256"
    qr_str=''
    sendfinal = '1%' + filename[12:21] +'%' + filename[:12] #与查询时同样的格式
    print(sendfinal)
    #连接过程
    t1 = MyThread(task1, args=(sendfinal,))
    t1.start()
    while t1.get_result() is None:
        i = 0  # 手动锁等有值
    real_hash=t1.get_result()
    #以上连接过程记得取消注释
    # real_hash='7721219291468978639874381678808231092376563591922100975992647583802653467622'#此处记得注释
    path = os.path.join(settings.MEDIA_DIR + '\\' + user_name, filename)
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(2024)
            if not data:
                break
            sha256.update(data)  # update添加时会进行计算
    Video_Hash = sha256.hexdigest()
    Video_Hash = str(int(Video_Hash,base = 16))
    print('Hash for local file:'+Video_Hash)
    print('realHash=' + real_hash)
    img_name=filename[:21]+"_AT_"+verifyTime[:10]+"_BY_"+Hash_tool

    #处理二维码
    os.chdir(settings.STATIC_DIR)
    if not (os.path.exists("qrcode")):
        os.makedirs("qrcode")



    if Video_Hash == real_hash:
        qr_str=("摄像头："+cameraName+"\n"
                "录制时间："+videoShotTime+"\n"
                "下载时间："+videoCreateTime+"\n"
                "验证时间："+verifyTime+"\n"
                "验证结果："+"未修改\n"
                "本地视频校验码："+Video_Hash+"\n"
                "原始视频校验码："+real_hash+"\n"
                "校验方式："+Hash_tool)
        os.chdir(settings.QRCODE_DIR)
        img=qrcode.make(qr_str)
        img_name=img_name+"_ORIGINAL"+".png"
        img.save(img_name)
        img_dir = os.path.join(settings.QRCODE_DIR, img_name)
        print(img_dir)
        return JsonResponse({'result': False,'imgName' : img_name})
    qr_str = ("摄像头：" + cameraName + "\n"
                "录制时间：" + videoShotTime + "\n"
                "下载时间：" + videoCreateTime + "\n"
                "验证时间：" + verifyTime + "\n"
                "验证结果：" + "已修改\n"
                "本地视频校验码：" + Video_Hash + "\n"
                "原始视频校验码：" + real_hash + "\n"
                "校验方式：" + Hash_tool)
    os.chdir(settings.QRCODE_DIR)
    img = qrcode.make(qr_str)
    img_name = img_name + "_MODIFIED" + ".png"
    img.save(img_name)
    img_dir=os.path.join(settings.QRCODE_DIR, img_name)
    print(img_dir)
    return JsonResponse({'result': True,'imgName':img_name})

@login_required
def query(request):#该函数已不用 留给超级管理员
    global videos_involved
    # tem_db = Mysql_service()
    datetime = request.POST
    print(type(datetime))
    print(datetime)
    if request.method == 'POST':
        print('postSuccess')
        data = json.loads(request.body)
        paraStr=data['param']
        print(paraStr)
        #get number 5n
        lastNo=int(paraStr[-1])
        if lastNo<5:
            lastNo=0
        else:
            lastNo=5
        paralist=paraStr.split('%')
        parafinal=paralist[2][:-1]+str(lastNo)+paralist[1]+'.mp4'#用来下载
        print(parafinal)
        sendfinal='1%'+paralist[1]+'%'+paralist[2][:-1]+str(lastNo)
        print(sendfinal)
        # temHash=tem_db.getHash(parafinal)

        t1 = MyThread(task1, args=(sendfinal,))
        t1.start()
        while t1.get_result() is None:
            i=0#手动锁等有值
        real_hash = t1.get_result()
        print('realHash='+real_hash)
        if real_hash=='-1':

            return JsonResponse({'result': 0})
        else:
            print(parafinal)
            return JsonResponse({'result': parafinal})


    return render(request, "q_all.html", {'title': '视频查询', 'filelist':videos_involved, 'videolist':json.dumps(videos_involved)})

class MyFTP(FTP):
    def makepasv(self):
        if self.af == socket.AF_INET:
            host, port = parse227(self.sendcmd('PASV'))
        else:
            host, port = parse229(self.sendcmd('EPSV'), self.sock.getpeername())
        # We tweak this so we don't use the internal ip returned by the remote server.
        # old: `return host, port`
        return self.host, port


def download_from_ftp(request):
    tem_db = Mysql_service()
    global user_name
    print('download____prepared')
    if request.method == 'POST':
        print('postSuccess')
        data = json.loads(request.body)
        vName = data['param']
        print(vName)
        print('vName='+str(vName))
        print(type(vName))
        # if str(os.getcwd()[-(5+len(user_name)+1):-(len(user_name)+1)]) != 'media':
        #     print(os.getcwd())
        #     print('88888')
        os.chdir(settings.MEDIA_DIR)  # 进入视频总文件夹，以后要加密

        if not (os.path.exists(user_name)):
            os.makedirs(user_name)
        os.chdir(os.getcwd() + '\\' + user_name)  #进入个人文件夹


        for filenames in vName:
            downloadInfo=tem_db.getDownload(filenames)
            ftpIp=downloadInfo[0]
            ftpUser=downloadInfo[1]
            ftpPwd=downloadInfo[2]
            ftpAdd=downloadInfo[3][0:downloadInfo[3].rfind('/',1)]

            print(ftpIp)
            print(ftpAdd)
            ftp = MyFTP(ftpIp)
            ftp.set_debuglevel(2)
            ftp.login(ftpUser, ftpPwd)
            # ftp.getwelcome()
            ftp.set_pasv(1)
            ftp.cwd(ftpAdd)
            print(ftp.pwd())
            ftp.retrlines('LIST')
            buf_size = 1024





            file_handler = open(filenames , 'wb+')

            ftp.retrbinary('RETR ' + filenames , file_handler.write, buf_size)
            file_handler.close()
            print('下载: %s' % (filenames  + "成功!"))
        ftp.quit()
        # os.chdir(settings.BASE_DIR)
    return JsonResponse({'result': 1})

# def upload_to_ftp():
#     ftp = MyFTP('39.100.228.145')
#     ftp.set_debuglevel(2)
#     ftp.login('thepmc', 'thepmc123')
#     ftp.getwelcome()
#     ftp.set_pasv(1)
#     ftp.cwd('video')
#     print(ftp.pwd())
#     ftp.retrlines('LIST')
#     # 下载
#     buf_size = 1024
#     file_handler = open('202002231205.mp4', 'wb+')
#     ftp.retrbinary('RETR 202002231205.mp4', file_handler.write, buf_size)
#     file_handler.close()
#     print('下载: %s' % '202002231205.mp4' + "成功!")
#     ftp.quit()





@login_required
def download(request):
    data = json.loads(request.body)
    print(data)
    return JsonResponse({})
