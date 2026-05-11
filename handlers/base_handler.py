import os


class BaseHandler:
    """모든 Handler가 공통으로 사용하는 경로/에러 처리"""

    @staticmethod
    def get_project_root():
        basedir = os.path.abspath(os.path.dirname(__file__))
        return os.path.dirname(basedir)

    @classmethod
    def get_config_path(cls):
        config_path = os.path.join(cls.get_project_root(), 'config')
        os.makedirs(config_path, exist_ok=True)
        return config_path

    @classmethod
    def get_instance_path(cls):
        instance_path = os.path.join(
            os.environ.get('RENDER_DISK_PATH', cls.get_project_root()), 'instance'
        )
        os.makedirs(instance_path, exist_ok=True)
        return instance_path

    @staticmethod
    def handle_error(error, context=""):
        msg = f'{context} 중 오류가 발생했습니다.' if context else '오류가 발생했습니다.'
        return {
            'success': False,
            'error': str(error),
            'message': msg
        }
