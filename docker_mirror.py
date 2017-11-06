#!/usr/bin/python
# coding=utf8

import platform
import re
import time
import os
import json

mirror_prefix = "--registry-mirror="

mirrors = {
    "netease": "http://hub-mirror.c.163.com"
    ,"ustc": "https://docker.mirrors.ustc.edu.cn"
    ,"official": "https://registry.docker-cn.com"
    #"aliyun": "https://2h3po24q.mirror.aliyuncs.com"  # use your own aliyun mirror url instead.
}

docker_config_map = {
    "Ubuntu": {
        "config": "/etc/default/docker",
        "prefix": "DOCKER_OPTS="
    },
    "CentOS Linux": {
        "config": "/etc/sysconfig/docker",
        "prefix": "OPTIONS="
    },
    "Darwin": {
        "config": "~/.docker/daemon.json",
        "prefix": ""
    }
}


def get_dist():
    return platform.linux_distribution()[0]


def get_config(dist):
    return docker_config_map[dist]["config"]


def get_prefix(dist):
    return docker_config_map[dist]["prefix"]


def get_new_options(option, mirror):
    option = option.strip()
    quota = option[len(option) - 1]
    if mirror_prefix in option:
        r1 = re.compile('[\'\"]')
        results1 = r1.split(option)

        r2 = re.compile('[\s]')
        results2 = r2.split(results1[1].strip())
        for i in range(len(results2)):
            if results2[i].startswith(mirror_prefix):
                results2[i] = mirror_prefix + mirror
        new_option = results1[0] + quota + " ".join(results2) + quota
    else:
        new_option = option[:-1] + " " + mirror_prefix + mirror + quota
    new_option += "\n"
    return new_option


def execute_sys_cmd(cmd):
    result = os.system(cmd)
    return result


def set_docker_config_for_mac(mirror):
    dist = platform.system()
    docker_config = get_config(dist)
    config = None
    origin_lines = None
    with open(os.path.expanduser(docker_config), 'r') as f:
        try:
            origin_lines = f.readlines()
            config = json.loads("".join(origin_lines))
        except ValueError as ve:
            print "invalid json format for file: {file}".format(file=docker_config)
            print "origin file is:\n{lines}".format(lines="".join(origin_lines))
    if config is not None:
        config["registry-mirrors"] = [mirror]
        with open(os.path.expanduser(docker_config), 'w') as f:
            try:
                json.dump(config, f)
                return True
            except Exception as exception:
                print "origin file lines is:\n{lines}".format(lines=origin_lines)
            
def set_docker_config(mirror):
    dist = get_dist()
    docker_config = get_config(dist)
    prefix = get_prefix(dist)
    new_line = ""
    options = ""
    with open(docker_config, "r") as f:
        for line in f:
            if line.startswith(prefix):
                options = get_new_options(line, mirror)
            else:
                new_line += line
        if options == "":
            options = prefix + "\'" + mirror_prefix + mirror + "\'"

    with open(docker_config, "w") as f:
        f.write(new_line)
        f.writelines(options)


def restart_docker_daemon():
    execute_sys_cmd("systemctl restart docker")

def get_full_image_name(mirror_url):
    return mirror_url.split("://")[-1] + "/library/centos"

def get_speed(mirror, mirror_url):
    if platform.system() == "Darwin":
        image_name = get_full_image_name(mirror_url)
    else:
        set_docker_config(mirror_url)
        restart_docker_daemon()
        image_name = "centos"

    execute_sys_cmd("docker rmi " + image_name + " -f 1> /dev/null 2>&1")

    print "pulling {image} from {mirror}".format(image=image_name, mirror=mirror)

    begin_time = time.time()

    execute_sys_cmd("docker pull " + image_name + " 1> /dev/null 2>&1")

    end_time = time.time()

    cost_time = end_time - begin_time

    print "mirror {mirror} cost time: {cost_time}\n".format(mirror=mirror, cost_time=cost_time)

    # delete centos images every time.
    execute_sys_cmd("docker rmi " + image_name + " -f 1> /dev/null 2>&1")

    return 204800 / cost_time 

if __name__ == "__main__": 
    max_speed = 0
    best_mirror = ""
    best_mirror_url = ""
    for k, v in mirrors.items():
        speed = get_speed(k, v)
        if speed > max_speed:
            max_speed = speed
            best_mirror = k
            best_mirror_url = v

    print "best mirror is: {mirror}, set docker config and restart docker daemon now.".format(mirror=best_mirror)

    if platform.system() == "Darwin":
        if set_docker_config_for_mac(best_mirror_url) is True:
            print "Please restart docker manually, more info is here: https://docs.docker.com/docker-for-mac"
        else:
            print "Please check your docker daemon config file, more info is here: https://docs.docker.com/docker-for-mac"
    else:
        set_docker_config(best_mirror_url)
        restart_docker_daemon()
