from datetime import datetime
from database.models import db, User, Chat, Message


class UserHandler:
    def get_user_history(self, anonymous_id):
        """사용자 채팅 히스토리 조회 (기존 로직 완벽 보존)"""
        try:
            user = User.query.filter_by(anonymous_id=anonymous_id).first()
            if not user:
                return {}

            chats = Chat.query.filter_by(user_id=user.id).order_by(Chat.created_at.desc()).all()
            history = {}

            for chat in chats:
                messages = [{'sender': msg.sender, 'text': msg.text} for msg in chat.messages]
                history[chat.id] = {
                    'id': chat.id,
                    'title': chat.title,
                    'messages': messages
                }

            return history

        except Exception as e:
            print(f"히스토리 조회 오류: {e}")
            return {}

    def get_user_info(self, anonymous_id):
        """사용자 정보 조회"""
        try:
            user = User.query.filter_by(anonymous_id=anonymous_id).first()
            if user:
                return {
                    'success': True,
                    'id': user.id,
                    'anonymous_id': user.anonymous_id
                }
            else:
                return {
                    'success': False,
                    'message': '사용자를 찾을 수 없습니다.'
                }
        except Exception as e:
            print(f"사용자 조회 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '사용자 정보를 가져오는 중 오류가 발생했습니다.'
            }

    def create_user(self, anonymous_id):
        """사용자 생성"""
        try:
            if not anonymous_id:
                return {
                    'success': False,
                    'error': 'anonymous_id가 필요합니다.',
                    'message': '익명 ID를 입력해주세요.'
                }

            # 이미 존재하는지 확인
            existing_user = User.query.filter_by(anonymous_id=anonymous_id).first()
            if existing_user:
                return {
                    'success': True,
                    'id': existing_user.id,
                    'anonymous_id': existing_user.anonymous_id,
                    'message': '이미 존재하는 사용자입니다.'
                }

            # 새 사용자 생성
            user = User(anonymous_id=anonymous_id)
            db.session.add(user)
            db.session.commit()

            return {
                'success': True,
                'id': user.id,
                'anonymous_id': user.anonymous_id,
                'message': '사용자가 성공적으로 생성되었습니다.'
            }

        except Exception as e:
            db.session.rollback()
            print(f"사용자 생성 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '사용자 생성 중 오류가 발생했습니다.'
            }

    def get_users_stats(self):
        """전체 사용자 통계"""
        try:
            total_users = User.query.count()
            total_chats = Chat.query.count()
            total_messages = Message.query.count()

            return {
                'success': True,
                'total_users': total_users,
                'total_chats': total_chats,
                'total_messages': total_messages,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"사용자 통계 조회 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': '사용자 통계를 가져오는 중 오류가 발생했습니다.'
            }


# 전역 인스턴스 생성
user_handler = UserHandler()