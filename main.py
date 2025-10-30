import uvicorn

from config import PORT


def main():
    uvicorn.run("app:app", host="0.0.0.0", port=int(PORT), reload=True)


if __name__ == "__main__":
    main()
