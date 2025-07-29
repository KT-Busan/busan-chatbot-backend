import os
import requests
import xml.etree.ElementTree as ET
from datetime import date
from database.models import JobPosting


def get_job_postings_from_db():
    """DB에서 현재 모집 중인 일자리 정보 조회"""
    today = date.today()
    postings = JobPosting.query.filter(JobPosting.end_date >= today) \
        .order_by(JobPosting.end_date.asc()) \
        .limit(3).all()

    if not postings:
        return "현재 모집 중인 일자리 지원 사업을 찾지 못했어요. 관리자가 데이터를 업데이트할 때까지 기다려주세요!"

    result_text = "📋 **현재 모집 중인 사업** 중 마감이 임박한 3개 사업을 알려드릴게요!\n\n"
    for post in postings:
        result_text += f"**🎯 {post.title}**\n"
        result_text += f"   • **담당 기관:** {post.organization}\n"
        result_text += f"   • **신청 기간:** {post.period}\n"
        # 지원 대상 정보 추가 (50자까지 요약)
        if post.target:
            target_summary = (post.target[:50] + '...') if len(post.target) > 50 else post.target
            result_text += f"   • **지원 대상:** {target_summary}\n"
        result_text += "\n"

    result_text += "💡 더 자세한 정보는 사업명을 포함해서 질문해주시거나, [부산청년플랫폼](https://young.busan.go.kr/policySupport/list.nm)에서 확인하실 수 있습니다."
    return result_text


def get_public_sector_jobs():
    """공공데이터포털 '부산광역시_공공부문 일자리(채용) 정보' API 호출"""
    service_key = os.getenv("GO_DATA_SERVICE_KEY")
    if not service_key:
        return "공공데이터포털 API 키가 설정되지 않았습니다."

    url = 'http://apis.data.go.kr/6260000/JobInst/getJobInst'
    params = {
        'serviceKey': service_key,
        'numOfRows': '5',  # 최신 5개 정보 요청
        'pageNo': '1',
        'resultType': 'xml'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        # XML 데이터 파싱
        root = ET.fromstring(response.content)
        items = root.findall('./body/items/item')

        if not items:
            return "현재 조회 가능한 최신 공공부문 일자리 정보가 없습니다."

        result_text = "🏛️ **최신 부산시 공공부문 일자리 정보**입니다.\n\n"
        for item in items:
            def find_text(tag):
                return item.findtext(tag, '정보 없음')

            result_text += f"**📋 {find_text('title')}**\n"
            result_text += f"   • **기관명:** {find_text('instNm')}\n"
            result_text += f"   • **담당부서:** {find_text('deptNm')}\n"
            result_text += f"   • **채용담당자:** {find_text('empCharger')}\n"
            result_text += f"   • **채용분야:** {find_text('empfield')}\n"
            result_text += f"   • **근무형태:** {find_text('workForm')}\n"
            result_text += f"   • **근무지역:** {find_text('workRegion')}\n"
            result_text += f"   • **접수기간:** {find_text('receptStartdate')} ~ {find_text('receptEnddate')}\n"
            result_text += f"   • **접수방법:** {find_text('receptMth')}\n"
            detail_text = find_text('detail')
            if len(detail_text) > 100:
                detail_text = detail_text[:100] + '...'
            result_text += f"   • **세부내용:** {detail_text}\n\n"

        return result_text

    except requests.exceptions.RequestException as e:
        print(f"공공데이터 API 호출 오류: {e}")
        return "최신 일자리 정보를 가져오는 데 실패했습니다. 잠시 후 다시 시도해주세요."
    except ET.ParseError as e:
        print(f"XML 파싱 오류: {e}")
        return "정보를 분석하는 데 실패했습니다. 데이터 형식이 올바르지 않을 수 있습니다."


def get_external_data(user_query):
    """외부 API 데이터 가져오기 (날씨 등)"""
    if "날씨" in user_query:
        API_KEY = os.getenv("OPENWEATHER_API_KEY")
        if not API_KEY:
            return "날씨 API 키가 설정되지 않았습니다."

        BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
        params = {'q': 'Busan', 'appid': API_KEY, 'lang': 'kr', 'units': 'metric'}

        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            description = data['weather'][0]['description']
            temp = data['main']['temp']
            return f"🌤️ 현재 부산 날씨는 '{description}'이며, 기온은 {temp}°C 입니다."
        except requests.exceptions.RequestException as e:
            print(f"날씨 API 호출 오류: {e}")
            return "날씨 정보를 가져오는 데 실패했습니다."

    return None