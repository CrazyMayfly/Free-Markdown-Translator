import threading

import translators as ts


class GoogleTrans(object):
    def translate(self, sourceTxt, srcLang, targetLang, retries=0):
        print(
            f"{threading.current_thread().name} is translating {srcLang} to {targetLang}, length={len(sourceTxt)}"
        )
        if retries > 5:
            return ""
        try:
            result = ts.translate_text(
                sourceTxt,
                translator="google",
                from_language=srcLang,
                to_language=targetLang,
                if_ignore_limit_of_length=True,
                if_show_time_stat=True,
            )
            if result is None:
                retries += 1
                print("retry ", retries)
                return self.translate(sourceTxt, srcLang, targetLang, retries)
            else:
                return result
        except Exception as e:
            print(e)
            retries += 1
            print("retry ", retries)
            return self.translate(sourceTxt, srcLang, targetLang, retries)
