from move_app import Move_app
from core_utils import CoreUtils
import traceback

VOICE_TEXT = "Hello I am a voice server?"

logger = CoreUtils.getLogger("test_voice_server")

logger.debug("start test_voice server")
move_app = Move_app()
try:
    move_app.sayText(VOICE_TEXT)
except Exception:
  logger.debug(traceback.format_exc())
  logger.debug("close voice server")