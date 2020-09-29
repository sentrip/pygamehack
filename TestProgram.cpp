
#include <array>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>


struct Level {
	uint32_t id{ 321 };
	float duration{ 0.5f };
	double long_stuff{ 25.0 };

	Level(uint32_t id = 321, float duration = 0.5f, double long_stuff = 25.0)
		: id(id), duration(duration), long_stuff(long_stuff) {}
};

struct Game {
	uint32_t selected_index{ 4 };
	Level* previous_level{nullptr};
	Level l;
};

struct Application {
	static uint32_t marker;
	static Application main;

	uint32_t power_0{ 1 << 0 },
			 power_1{ 1 << 1 },
			 power_2{ 1 << 2 },
			 power_3{ 1 << 3 },
			 power_4{ 1 << 4 };

	Game game;

	uint32_t* v_ptr;
	Game* game_ptr;
	char* str;
	const char* const_str;

	std::vector<uint32_t> values;
	std::vector<std::vector<uint32_t>> nested_values;
	std::vector<Level> levels;


	Application() {
		v_ptr = new uint32_t{ 12 };  
		game_ptr = new Game{};
		str = new char[64]{ "My very nice dynamic string" };
		const_str = "My very nice constant string";
		for (uint32_t i = 0; i < 17; ++i) { values.push_back(i); } 
		for (uint32_t i = 0; i < 3; ++i) { std::vector<uint32_t> vs; for (uint32_t j = 0; j < 5; ++j) { vs.push_back(j); } nested_values.push_back(vs); }
		for (uint32_t i = 0; i < 7; ++i) { levels.push_back(Level{500 + i * 20, i * 0.5f, i * 50.0}); }

		game_ptr->previous_level = &levels[0];
		game.previous_level = &levels[1];
	}
	
	~Application() { delete v_ptr; delete game_ptr; delete[] str; }

	void run() { 
		std::cout << "marker                      - " << "0x" << std::hex << &Application::marker << std::endl;
		std::cout << "App                         - " << "0x" << std::hex << this << std::endl;
		std::cout << "App.v_ptr                   - " << "0x" << std::hex << v_ptr << std::endl;
		std::cout << "App.game_ptr                - " << "0x" << std::hex << game_ptr << std::endl;
		std::cout << "App.str                     - " << "0x" << std::hex << (void*)str << std::endl;
		std::cout << "App.const_str               - " << "0x" << std::hex << (void*)const_str << std::endl;

		std::cout << "App.game.previous_level     - " << "0x" << std::hex << game.previous_level << std::endl;
		std::cout << "App.game_ptr.previous_level - " << "0x" << std::hex << game_ptr->previous_level << std::endl;

		std::cout << "App.values.begin            - " << "0x" << std::hex << (void*)values.data() << std::endl;
		for (uint32_t i = 0; i < 3; ++i) {
			std::cout << "App.nested_values[" << i << "].begin  - " << "0x" << std::hex << (void*)nested_values[i].data() << std::endl;
		}
		std::cout << "App.levels.begin            - " << "0x" << std::hex << (void*)levels.data() << std::endl;

		while (true) { std::this_thread::sleep_for(std::chrono::milliseconds(1)); } 
	}
};

uint32_t Application::marker = 1234567898;
Application Application::main{};


int main(int argv, char** argc)
{
	Application::main.run();
	return 0;
}