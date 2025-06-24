from flask import Flask, render_template, request, jsonify
import openai
import pandas as pd

# OpenAI API 키 설정
openai.api_key = ""  # 여기에 발급받은 API 키를 입력하세요.


app = Flask(__name__)

# 동의어 사전 설정
industry_synonyms = {
    "건설업": ["건설", "공사", "건축", "시공"],
    "제조업": ["제작", "제조", "가공", "생산"],
    "운송업": ["운송", "운반", "교통", "물류", "배송"],
    "농업": ["농사", "농업", "농장", "경작"],
    "어업": ["어업", "수산", "양식"],
    "광업": ["광업", "채굴", "광산"],
    "서비스업": ["서비스", "서비스업", "접객업", "요식업", "레저업"],
    "의료업": ["의료", "병원", "보건", "치료"],
    # 추가 업종 동의어
}

disaster_synonyms = {
    "떨어짐": ["추락", "낙하", "떨어짐", "낙상"],
    "화재": ["불", "화염", "화재", "발화"],
    "붕괴": ["무너짐", "붕괴", "손상", "구조물 붕괴"],
    "중독": ["중독", "화학물질 노출", "독성 물질", "유독가스"],
    "질식": ["질식", "산소 결핍", "호흡 곤란"],
    "사고": ["사고", "재해", "사고 발생", "재난"],
    "폭발": ["폭발", "폭파", "발파"],
    "감전": ["감전", "전기 충격", "전기 사고"],
    # 추가 사고 유형 동의어
}

# 동의어를 매핑하는 함수
def map_synonyms(text, synonyms_dict):
    for key, synonyms in synonyms_dict.items():
        for synonym in synonyms:
            if synonym in text:
                return key
    return text  # 매핑된 동의어가 없으면 원본 텍스트 반환

# 엑셀 파일에서 데이터를 불러오는 함수
def load_disaster_data(file_path):
    df = pd.read_excel(file_path)
    return df

# 질문에서 업종과 사고 유형을 추출하는 함수
def extract_keywords_from_text(text, industry_list, disaster_list):
    # 동의어 매핑 적용
    text = map_synonyms(text, industry_synonyms)
    text = map_synonyms(text, disaster_synonyms)

    # 업종과 사고 유형을 문자열로 변환하여 NaN 값 문제 방지
    industry_list = [str(ind) for ind in industry_list if pd.notna(ind)]
    disaster_list = [str(dis) for dis in disaster_list if pd.notna(dis)]
    
    # 업종 추출
    industry = next((ind for ind in industry_list if ind in text), None)
    # 사고 유형 추출
    disaster_type = next((dis for dis in disaster_list if dis in text), None)
    
    return industry, disaster_type

# 업종과 사고 유형에 따라 대표적인 사례를 검색하는 함수
def get_disaster_info_for_industry_and_type(industry, disaster_type, df):
    # '업종'과 '재해 유형' 열을 기준으로 필터링
    if industry and disaster_type:
        filtered_data = df[(df['업종'].str.contains(industry, case=False, na=False)) &
                           (df['재해 유형'].str.contains(disaster_type, case=False, na=False))]
    elif industry:
        # 업종만 지정되었을 때 해당 업종의 모든 사고 유형을 필터링
        filtered_data = df[df['업종'].str.contains(industry, case=False, na=False)]
    else:
        return "질문에서 업종이나 사고 유형을 확인할 수 없습니다. 예: '건설업에서 일어날 수 있는 떨어짐 사고에 대해 알려줘'."

    if filtered_data.empty:
        return f"{industry} 업종에서 '{disaster_type}' 사고에 대한 정보를 찾을 수 없습니다."

    # 사례가 5개 미만이면 모두 출력하고, 최대 5개까지 선택
    limited_data = filtered_data.head(5).to_dict(orient='records')

    # '사고 내용' 열이 존재하지 않을 때 기본 메시지 추가
    case_list = "\n".join(
        [f"{idx+1}. {case.get('사고 내용', '사고 내용 정보가 없습니다.')}" for idx, case in enumerate(limited_data)]
    )

    # GPT 모델에 요약 요청
    prompt = f"다음은 '{industry}' 업종에서 발생할 수 있는 '{disaster_type}' 사고의 대표적인 사례입니다:\n{case_list}\n이 정보를 간단히 요약해 주세요."

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "당신은 한국어로 답변하는 도움이 되는 어시스턴트입니다."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )

    return response['choices'][0]['message']['content'].strip()

# HTML 템플릿 제공
@app.route('/')
def index():
    return render_template('chatbot.html')

# 챗봇 API 엔드포인트
@app.route('/api/chatbot', methods=['POST'])
def chatbot_response():
    data = request.get_json()
    user_input = data.get('text', '')

    # 엑셀 파일에서 업종 및 사고 유형 목록 가져오기
    industry_list = df['업종'].unique()
    disaster_list = df['재해 유형'].unique()

    # 질문에서 업종 및 사고 유형 추출
    industry, disaster_type = extract_keywords_from_text(user_input, industry_list, disaster_list)
    
    if industry:
        disaster_response = get_disaster_info_for_industry_and_type(industry, disaster_type, df)
    else:
        disaster_response = "질문에서 업종이나 사고 유형을 확인할 수 없습니다. 예: '건설업에서 일어날 수 있는 떨어짐 사고에 대해 알려줘'."

    return jsonify({'response': disaster_response})

if __name__ == '__main__':
    # 하나의 엑셀 파일 로드
    excel_file_path = r"C:\Users\김세진\Desktop\GPT\serious disaster accident.xlsx"
    df = load_disaster_data(excel_file_path)
    app.run(debug=True)