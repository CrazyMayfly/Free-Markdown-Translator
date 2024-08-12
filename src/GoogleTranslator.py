import logging
import translators as ts

MAX_RETRY = 5


class GoogleTrans:
    def translate(self, sourceTxt, srcLang, targetLang, retries=0):
        logging.debug(f"Translating {srcLang} to {targetLang}, length={len(sourceTxt)}, retries={retries}")
        if retries >= MAX_RETRY:
            return ""
        try:
            result = ts.translate_text(
                sourceTxt,
                translator="google",
                from_language=srcLang,
                to_language=targetLang,
                if_ignore_limit_of_length=True,
                if_show_time_stat=False,
            )
            if result is None:
                retries += 1
                logging.warning(f"Translate failed, retry {retries}/{MAX_RETRY}")
                return self.translate(sourceTxt, srcLang, targetLang, retries)
            return result
        except Exception as e:
            retries += 1
            logging.error(f"Translate error, retry {retries}/{MAX_RETRY}")
            logging.error(e)
            return self.translate(sourceTxt, srcLang, targetLang, retries)
