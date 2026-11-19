import hashlib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score,confusion_matrix
LABELS=['labor','housing','consumer']
def classify(text):
    bases={'labor':['工资拖欠 工时 劳动 合同 加班 报酬 单位 用工','公司没有发工资 劳动报酬 加班工时 拖欠薪水','用工单位 劳动合同 薪资 考勤 解除工作'], 'housing':['租房 住房 房屋 租赁 押金 房东 退租 维修','租赁房屋到期 房东不退押金 租房维修','住房租约 退租 租金 房屋漏水 物业'], 'consumer':['购物 消费 商品 退款 质量 订单 商家 收据','商家出售商品损坏 消费退款 订单 收据','购买电器 商品质量 保修 消费者 退款']}
    texts=[];ys=[]
    for label,phrases in bases.items():
        for i in range(36):texts.append(phrases[i%len(phrases)]+f' 模拟行政来访编号{i} '+'请协助登记分流');ys.append(label)
    train,test=train_test_split(np.arange(len(texts)),test_size=.25,random_state=34,stratify=ys)
    model=make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(2,3)),MultinomialNB(alpha=.5)).fit([texts[i] for i in train],[ys[i] for i in train])
    predicted=model.predict([texts[i] for i in test]);proba=model.predict_proba([text])[0];idx=int(np.argmax(proba));label=str(model.classes_[idx]);confidence=float(proba[idx])
    return label,confidence,{'macro_f1':float(f1_score([ys[i] for i in test],predicted,average='macro')),'confusion_matrix':confusion_matrix([ys[i] for i in test],predicted,labels=LABELS).tolist(),'labels':LABELS,'train_count':len(train),'test_count':len(test),'seed':34,'threshold':.68,'dataset_sha256':hashlib.sha256(chr(10).join(texts).encode()).hexdigest(),'source':'主题模板合成文本，仅验证内部行政分流；不是法律意见'}
