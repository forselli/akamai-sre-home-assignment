import httpx


def fetch_characters(url, page):
    # print(f"Fetching page {page}")
    response = httpx.get(url + str(page))
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(
            f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
        )
        return False
    return response.json()


def filter_request(characters):
    for character in characters:
        if "Earth" in character["origin"]["name"]:
            # print(
            #     f"Found character {character['name']} on {character['origin']['name']}"
            # )
            yield character


def main():
    BASE_URL = (
        "https://rickandmortyapi.com/api/character?species=Human&status=Alive&page="
    )
    all_data_results = []
    page = 1

    # Fetch the first page outside the loop to get the total number of pages
    characters = fetch_characters(BASE_URL, page)
    if characters is False:
        return

    total_pages = characters["info"]["pages"]

    # Process the first page
    data_results = filter_request(characters["results"])
    all_data_results.extend(data_results)

    # Iterate through the remaining pages
    for page in range(2, total_pages + 1):
        characters = fetch_characters(BASE_URL, page)
        if characters is False:
            break
        data_results = filter_request(characters["results"])
        all_data_results.extend(data_results)

    print(all_data_results)


if __name__ == "__main__":
    main()
