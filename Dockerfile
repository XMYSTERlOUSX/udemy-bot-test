FROM sammax23/rcmltb

ENV LANG en_US.utf8
ENV LC_ALL en_US.UTF-8
ENV LANGUAGE en_US:en
ENV TZ=Asia/Kolkata DEBIAN_FRONTEND=noninteractive

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt -qq update --fix-missing
RUN apt-get install -y git p7zip-full tree
RUN apt-get upgrade -y
# RUN apt-get -qq purge git
RUN apt-get -y autoremove
RUN apt-get -y autoclean

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN cp bin/mp4decrypt /usr/bin
RUN cp bin/N_m3u8DL-RE /usr/bin

RUN chmod +x /usr/bin/mp4decrypt
RUN chmod +x /usr/bin/N_m3u8DL-RE

RUN chmod 777 /usr/src/app

CMD ["bash","start.sh"]
