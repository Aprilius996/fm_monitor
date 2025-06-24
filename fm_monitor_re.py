import re
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import smtplib
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess
import chardet

un_pattern = re.compile(r"(.*?)通告(\d{4})年第(\d+)号", re.I)

def un_link():
    url = "https://www.mfa.gov.cn/web/wjb_673085/zfxxgk_674865/gknrlb/jytz/"
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"无法加载页面:{e}")
        return None
    
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    #print(soup)
    
    links = soup.select("div.opinion-ul ul li a")
    #print(links)
    
    result = []
    for link in links:
        title = link.get_text(strip=True)
        #print(f"原始标题: [{title}]")
        #print(title)
        href = link.get("href")
        #print(href)
        match = un_pattern.search(title)
        #print(match)
        
        if match:
            year = int(match.group(2))
            number = int(match.group(3))
            #print("前缀：", match.group(1))
            #print("年份：", match.group(2))
            #print("编号：", match.group(3))
            
            if (year == 2025 and number >= 8) or (year >2025):
                result.append({
                    "year": year,
                    "number": number,
                    "title": title,
                    "url": href
                })
        return result
        

def send_email(subject, body, from_addr, to_addr, smtp_server, smtp_port, password):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = formataddr(("外交部监测脚本", from_addr))
    msg["To"] = formataddr(("收件人", to_addr))
    msg["Subject"] = Header(subject, "utf-8")
    
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(from_addr, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
        server.quit()
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败:{e}")


if __name__ == "__main__":
    sent_file = "sent_urls.txt"
    sent_urls = set()
    if os.path.exists(sent_file):
        with open(sent_file, "r") as f:
            sent_urls = set(line.strip() for line in f)
            
    result = un_link()
    if result:
        target_url = result[0]["url"]
        if target_url and target_url not in sent_urls:
            print(f"发现新的联合国制裁通知:{target_url}")
            send_email(
                subject = "外交部转发联合国制裁通知",
                body = f"发现新的联合国制裁通知:{target_url}",
                from_addr = os.getenv("FROM_ADDR"),
                to_addr = os.getenv("TO_ADDR"),
                smtp_server = os.getenv("SMTP_SERVER", "smtp.qq.com"),
                smtp_port = 465,
                password = os.getenv("SMTP_PASSWORD")
            )
    
            with open(sent_file, "a") as f:
                f.write(target_url + "\n")
            
            subprocess.run(["git", "add", sent_file])
            subprocess.run(["git", "commit", "-m", "Update sent URLs"])
            subprocess.run(["git", "push"])