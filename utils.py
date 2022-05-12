
def get_country(geoid):
    match geoid:
        case "f4":
            return "US"
        case "292d":
            return "XE"
        case "7c":
            return "JP"
        case "27":
            return "CA"
        case "f2":
            return "GB"
        case "54":
            return "FR"
        case "b0":
            return "NL"
        case "dd":
            return "SE"
        case "xe":
            return "AT"
        case "5e":
            return "DE"
        case "989e":
            return "XW"
        case "68":
            return "HK"
        case "a7":
            return "MY"
        case "d7":
            return "SG"
        case "xc":
            return "AU"
            
def get_release_by_country(country, album):
    releases = int(album['release-count'])-int("1")
    try:
        for i in range(releases):
            x = int("%d" % (i))
            if album["release-list"][x]["country"] == country:
                return x
            elif x == releases:
                return 0
    except:
        return 0